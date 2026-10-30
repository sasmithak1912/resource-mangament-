from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import math

app = FastAPI()

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Load hospital dataset
df = pd.read_csv("hospital_insights_summary_cleaned (1).csv")


# ---------------- HOME ----------------

@app.get("/")
def home():
    return {
        "message": "Hospital Management Backend is Running"
    }


# ---------------- SUMMARY ----------------

@app.get("/api/summary")
def summary():
    return {
        "total_records": len(df),
        "total_columns": len(df.columns)
    }


# ---------------- COLUMNS ----------------

@app.get("/api/columns")
def columns():
    return {
        "columns": df.columns.tolist()
    }


# ---------------- INSIGHTS ----------------

@app.get("/api/insights")
def insights():

    highest_occupancy = df.loc[
        df["max_occupancy"].idxmax()
    ]

    highest_admissions = df.loc[
        df["patients_admitted"].idxmax()
    ]

    lowest_satisfaction = df.loc[
        df["avg_satisfaction"].idxmin()
    ]

    return {
        "highest_occupancy_service":
            highest_occupancy["service"],

        "highest_occupancy":
            float(highest_occupancy["max_occupancy"]),

        "highest_admission_service":
            highest_admissions["service"],

        "highest_admissions":
            int(highest_admissions["patients_admitted"]),

        "lowest_satisfaction_service":
            lowest_satisfaction["service"],

        "lowest_satisfaction":
            float(lowest_satisfaction["avg_satisfaction"])
    }


# ---------------- RESOURCES ----------------

@app.get("/api/resources")
def resources():

    result = []

    for _, row in df.iterrows():

        difference = (
            int(row["staff_count"])
            - int(row["recommended_staff"])
        )

        if difference < 0:
            status = "Staff Shortage"
        elif difference == 0:
            status = "Adequate"
        else:
            status = "Staff Available"

        result.append({
            "service": row["service"],
            "staff_count": int(row["staff_count"]),
            "recommended_staff":
                int(row["recommended_staff"]),
            "staff_difference": difference,
            "status": status
        })

    return {
        "resources": result
    }


# ---------------- SERVICES ----------------

@app.get("/api/services")
def services():

    result = (
        df.groupby("service")
        .agg(
            total_patients=("patients_admitted", "sum"),
            average_stay=("avg_stay", "mean"),
            average_satisfaction=("avg_satisfaction", "mean"),
            maximum_occupancy=("max_occupancy", "max"),
            current_staff=("staff_count", "mean"),
            recommended_staff=("recommended_staff", "mean")
        )
        .reset_index()
    )

    return result.to_dict(orient="records")


# ==================================================
# LIVE PATIENT MANAGEMENT
# ==================================================

# Create a copy for live changes
live_df = df.copy()


# ---------------- LIVE STATUS ----------------

@app.get("/api/live-status")
def live_status():

    result = []

    for service in live_df["service"].unique():

        data = live_df[
            live_df["service"] == service
        ].iloc[-1]

        patients = int(data["patients_admitted"])
        staff = int(data["staff_count"])

        required_staff = max(
            int(data["recommended_staff"]),
            math.ceil(patients / 5)
        )

        result.append({
            "service": service,
            "patients": patients,
            "current_staff": staff,
            "required_staff": required_staff,
            "staff_difference":
                staff - required_staff
        })

    return {
        "live_status": result
    }


# ---------------- ADD PATIENT ----------------

@app.post("/api/add-patient")
def add_patient(
    service: str,
    patients: int = 1
):

    if service not in live_df["service"].unique():

        return {
            "success": False,
            "message": "Service not found"
        }

    if patients <= 0:

        return {
            "success": False,
            "message":
                "Patient number must be greater than 0"
        }

    # Find latest row for that service
    index = live_df[
        live_df["service"] == service
    ].index[-1]

    # Increase patients
    live_df.loc[
        index,
        "patients_admitted"
    ] += patients

    new_total = int(
        live_df.loc[
            index,
            "patients_admitted"
        ]
    )

    return {
        "success": True,
        "service": service,
        "patients_added": patients,
        "total_patients": new_total,
        "message": "Patient added successfully"
    }


# ---------------- EMERGENCY ----------------

@app.post("/api/emergency")
def emergency(
    service: str,
    patients: int = 1,
    severity: str = "HIGH"
):

    if service not in live_df["service"].unique():

        return {
            "success": False,
            "message": "Service not found"
        }

    if patients <= 0:

        return {
            "success": False,
            "message":
                "Patient number must be greater than 0"
        }

    severity = severity.upper()

    if severity not in [
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    ]:

        return {
            "success": False,
            "message":
                "Severity must be LOW, MEDIUM, HIGH or CRITICAL"
        }

    # Find latest service row
    index = live_df[
        live_df["service"] == service
    ].index[-1]

    # Add emergency patients
    live_df.loc[
        index,
        "patients_admitted"
    ] += patients

    new_total = int(
        live_df.loc[
            index,
            "patients_admitted"
        ]
    )

    return {
        "success": True,
        "service": service,
        "emergency_patients": patients,
        "total_patients": new_total,
        "severity": severity,
        "alert": "EMERGENCY REGISTERED"
    }


# ---------------- RESET DATA ----------------

@app.post("/api/reset")
def reset():

    global live_df

    live_df = df.copy()

    return {
        "success": True,
        "message": "Live data reset successfully"
    }