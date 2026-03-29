# google-alloydb-ai-ticket-intelligence

Build a small AI-enabled database feature using AlloyDB for PostgreSQL that enables users to query a custom dataset using natural language and receive meaningful results.

# 🎫 AlloyDB AI Support Ticket Intelligence

An AI-enabled support ticket system built on **Google AlloyDB for PostgreSQL**, enabling natural language queries over a custom dataset using **Gemini** and **pgvector**. The backend is a **FastAPI** app deployed on **Google Cloud Run**.

---

## Architecture Overview

```
User / Client
     │
     ▼
Cloud Run (FastAPI app)
     │
     ├──► AlloyDB (PostgreSQL + pgvector + google_ml_integration)
     │         └── Gemini embeddings & text generation via AlloyDB AI
     │
     └──► Google Cloud Storage (ticket attachments / images)
```

**Key GCP services used:**

| Service                             | Purpose                                      |
| ----------------------------------- | -------------------------------------------- |
| AlloyDB for PostgreSQL              | Primary database with vector + AI extensions |
| Cloud Run                           | Serverless hosting for the FastAPI app       |
| Vertex AI / Gemini                  | LLM for text generation and embeddings       |
| Cloud Storage                       | Image/attachment storage                     |
| VPC Peering + Serverless VPC Access | Private connectivity to AlloyDB              |

---

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and authenticated
- A GCP project with billing enabled
- Python 3.10+
- `psql` client (for direct DB access)
- Docker (used by Cloud Run source deploys)

---

## Setup Guide

### 1. Authenticate and Set Project

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Enable Required APIs

```bash
gcloud services enable \
  alloydb.googleapis.com \
  compute.googleapis.com \
  aiplatform.googleapis.com \
  run.googleapis.com \
  vpcaccess.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com
```

### 3. Create VPC Network and Subnet

AlloyDB requires a VPC with private service access (VPC peering). It is **not publicly accessible**.

```bash
gcloud compute networks create alloydb-network --subnet-mode=custom

gcloud compute networks subnets create alloydb-subnet \
  --network=alloydb-network \
  --region=us-central1 \
  --range=10.0.0.0/24

gcloud compute addresses create alloydb-ip-range \
  --global \
  --purpose=VPC_PEERING \
  --addresses=10.10.0.0 \
  --prefix-length=16 \
  --network=alloydb-network

gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=alloydb-ip-range \
  --network=alloydb-network
```

### 4. Create AlloyDB Cluster and Instance

```bash
gcloud alloydb clusters create ticket-cluster \
  --region=us-central1 \
  --network=projects/YOUR_PROJECT_ID/global/networks/alloydb-network \
  --password=YOUR_DB_PASSWORD

gcloud alloydb instances create ticket-instance \
  --cluster=ticket-cluster \
  --region=us-central1 \
  --instance-type=PRIMARY \
  --cpu-count=2
```

Get the private IP of the instance:

```bash
gcloud alloydb instances describe ticket-instance \
  --cluster=ticket-cluster \
  --region=us-central1 \
  --format="value(ipAddress)"
```

> **Note:** AlloyDB only has a private IP. You must connect from within the same VPC.

### 5. Connect to the Database via a Jump VM

Since AlloyDB has no public IP, create a VM inside the VPC to act as a bastion:

```bash
gcloud compute instances create alloydb-vm \
  --zone=us-central1-a \
  --network=alloydb-network \
  --subnet=alloydb-subnet \
  --machine-type=e2-micro \
  --image-family=debian-11 \
  --image-project=debian-cloud \
  --tags=alloydb

# Allow IAP-based SSH
gcloud compute firewall-rules create allow-iap-ssh \
  --network=alloydb-network \
  --allow=tcp:22 \
  --source-ranges=35.235.240.0/20 \
  --target-tags=alloydb

# SSH into the VM via IAP tunnel (no public IP needed)
gcloud compute ssh alloydb-vm \
  --zone=us-central1-a \
  --tunnel-through-iap
```

Inside the VM, install `psql` and connect:

```bash
sudo apt update && sudo apt install postgresql-client -y

psql "host=ALLOYDB_PRIVATE_IP port=5432 user=postgres password=YOUR_DB_PASSWORD dbname=postgres sslmode=require"
```

### 6. Enable AlloyDB AI Extensions

Run these SQL commands in your `psql` session:

```sql
CREATE EXTENSION IF NOT EXISTS google_ml_integration CASCADE;
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify
SELECT * FROM pg_extension;
```

### 7. Grant AlloyDB Service Agent Access to Vertex AI

The AlloyDB service account needs permission to call Gemini via Vertex AI:

```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-alloydb.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### 8. Register the Gemini Model in AlloyDB

Back in your `psql` session:

```sql
CALL google_ml.create_model(
  model_id             => 'gemini-flash',
  model_request_url    => 'https://aiplatform.googleapis.com/v1/projects/YOUR_PROJECT_ID/locations/global/publishers/google/models/gemini-2.0-flash:generateContent',
  model_qualified_name => 'gemini-2.0-flash',
  model_provider       => 'google',
  model_type           => 'llm',
  model_auth_type      => 'alloydb_service_agent_iam'
);

-- Verify
SELECT * FROM google_ml.list_models();

-- Test
SELECT google_ml.generate_text(
  model_id => 'gemini-flash',
  prompt   => 'Hello from AlloyDB AI'
);
```

---

## Local Development

### 1. Clone the Repository

```bash
git clone https://github.com/balbirkaur/google-alloydb-ai-support-ticket.git
cd google-alloydb-ai-support-ticket
```

### 2. Configure Environment Variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

| Variable          | Description                                                                                          |
| ----------------- | ---------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`    | PostgreSQL connection string (e.g. `postgresql+pg8000://postgres:PASSWORD@ALLOYDB_IP:5432/postgres`) |
| `GCS_BUCKET_NAME` | Your Cloud Storage bucket name for attachments                                                       |
| `GEMINI_API_KEY`  | Your Gemini API key (for direct API calls, if used)                                                  |

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Locally

> **Note:** You must run this from within a VM or environment that has network access to the AlloyDB private IP. From inside the `alloydb-vm`:

```bash
export DATABASE_URL="postgresql+pg8000://postgres:PASSWORD@ALLOYDB_PRIVATE_IP:5432/postgres"
export GCS_BUCKET_NAME="your-bucket-name"
export GEMINI_API_KEY="your-api-key"

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Deploying to Cloud Run

Cloud Run cannot directly reach AlloyDB's private IP without a **Serverless VPC Access connector**.

### 1. Create a Serverless VPC Connector

```bash
gcloud compute networks vpc-access connectors create alloydb-connector \
  --region=us-central1 \
  --network=alloydb-network \
  --range=10.9.0.0/28
```

### 2. Deploy the App

```bash
gcloud run deploy alloydb-ai-app \
  --source . \
  --region=us-central1 \
  --allow-unauthenticated \
  --vpc-connector=alloydb-connector \
  --vpc-egress=all-traffic \
  --set-env-vars "DATABASE_URL=postgresql+pg8000://postgres:PASSWORD@ALLOYDB_PRIVATE_IP:5432/postgres,GCS_BUCKET_NAME=your-bucket-name,GEMINI_API_KEY=your-api-key"
```

> **Important:** The `--vpc-egress=all-traffic` flag ensures all outbound traffic from Cloud Run goes through the VPC connector, allowing it to reach AlloyDB's private IP.

---

## Project Structure

```
.
├── app/
│   └── main.py          # FastAPI application entrypoint
├── .env.example         # Environment variable template
├── Dockerfile           # Container definition for Cloud Run
├── requirements.txt     # Python dependencies
└── README.md
```

**Python dependencies:**

- `fastapi` — web framework
- `uvicorn` — ASGI server
- `sqlalchemy` — ORM / database toolkit
- `pg8000` — pure-Python PostgreSQL driver

---

## Troubleshooting

**Cannot connect to AlloyDB from Cloud Run**
Make sure `--vpc-connector` and `--vpc-egress=all-traffic` are both set, and that the connector's IP range doesn't overlap with the AlloyDB subnet.

**`google_ml_integration` extension not available**
This extension is built into AlloyDB but may need to be explicitly created. Run `CREATE EXTENSION IF NOT EXISTS google_ml_integration CASCADE;` as the `postgres` superuser.

**`google_ml.generate_text` returns an error**
Verify the AlloyDB service agent has the `roles/aiplatform.user` IAM role (Step 7 above), and that the model URL and project ID are correct.

**SSH to bastion VM fails**
Ensure the `allow-iap-ssh` firewall rule exists and that your user account has the `roles/iap.tunnelResourceAccessor` IAM role.

---

## Security Notes

- **Never commit credentials.** The `.gitignore` excludes `.env` — keep all secrets there or use Secret Manager.
- Rotate the `postgres` database password and the Gemini API key before using this in production.
- Consider restricting Cloud Run to authenticated access (`--no-allow-unauthenticated`) for non-public APIs.

---

## License

MIT — see [LICENSE](LICENSE) for details.
