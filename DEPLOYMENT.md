# Deploy Yojana Saathi on Render

The repository includes `render.yaml`, which builds the React frontend and FastAPI backend into one public Render web service. The frontend and API share one origin, so the site uses the same `/api/v1` endpoints as local development.

## Create the public site

1. Sign in to Render and choose **New → Blueprint**.
2. Connect the GitHub repository `pratiksubedar/yojana_saathi` and select the `main` branch.
3. Render detects `render.yaml` and shows a service named `yojana-saathi`. Continue with the Blueprint setup.
4. When Render asks for `GROQ_API_KEY`, paste your Groq secret as the value. Do not add quotes, commit it to GitHub, or put it in a frontend variable.
5. Apply the Blueprint and wait for the service deploy to finish. The public address ends in `.onrender.com`.

If the key prompt does not appear, open the `yojana-saathi` service in Render, choose **Environment → Environment Variables**, add `GROQ_API_KEY` as the name and your Groq key as the value, save, then deploy the latest commit. The Blueprint sets `LLM_PRIMARY_PROVIDER=groq` and the configured Groq model.

## Local development

Keep the key in `backend/.env` (or the root `.env` used by your local setup):

```env
LLM_PRIMARY_PROVIDER=groq
GROQ_API_KEY=your_groq_key_here
```

`.env` files are ignored by Git. The example template is `backend/.env.example`.
