# Blog Application

A responsive blogging application built with **Python, Streamlit and MongoDB**.

## Features

- User registration and login with bcrypt password hashing
- MongoDB storage for users and blog posts
- Create, read, update and delete blog posts
- Browse all posts and search/filter by category
- Private dashboard showing only the signed-in user's posts
- User profile and logout
- Blue-and-white responsive interface

## Project structure

```text
Blog-Application/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
└── .streamlit/
    └── config.toml
```

## Run locally

1. Install Python 3.10 or newer.
2. Create and activate a virtual environment (recommended).
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root using `.env.example` as a template.
5. Set `MONGO_URI` to your MongoDB Atlas connection string.
6. In MongoDB Atlas, create a database user and allow network access from the machine that runs the app.
7. Start the application:

   ```bash
   streamlit run app.py
   ```

8. Open `http://localhost:8501`.

## MongoDB collections

The application creates a `blog_application` database with:

- `users`: username, email, bcrypt password hash and account creation date
- `blogs`: title, category, image URL, content, author and timestamps

## Deploy on Render

This is a Streamlit app, so deploy it as a **Render Web Service**:

1. Push this project to a GitHub repository. Do not commit `.env`.
2. In Render, create **New → Web Service** and connect the repository.
3. Use these settings:
   - Runtime: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT`
4. Add an environment variable named `MONGO_URI` in the Render service settings. Paste your MongoDB Atlas connection string as its value.
5. Deploy and open the public Render URL.

For MongoDB Atlas, configure network access to permit connections from the deployed service. For production, prefer a restricted network policy or private networking where available; avoid leaving the database open to the entire internet.

## Deploy on Streamlit Community Cloud

1. Push the project to GitHub.
2. Open Streamlit Community Cloud and create a new app from the repository.
3. Select `app.py` as the main file.
4. In the app's **Settings → Secrets**, add:

   ```toml
   MONGO_URI = "mongodb+srv://USERNAME:PASSWORD@CLUSTER.mongodb.net/"
   ```

5. Deploy the app.

## Security notes

- Passwords are hashed with bcrypt; plain-text passwords are not stored.
- `.env` and Streamlit secrets must never be committed to GitHub.
- Blog edit and delete database operations check the post author.
- Streamlit session state is used for the demo login flow. It is not a substitute for a production identity provider or hardened server-side session system. For a public production service, use a mature authentication provider or signed, expiring sessions, HTTPS, rate limiting, account recovery and security monitoring.
- Validate and moderate user-generated content and image URLs before exposing the app publicly.

## Troubleshooting

- **MongoDB connection error:** verify `MONGO_URI`, database credentials, Atlas network access and special-character URL encoding in the password.
- **Missing package:** run `pip install -r requirements.txt`.
- **Render port error:** make sure the start command uses `$PORT` and `--server.address 0.0.0.0`.
