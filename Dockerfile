# Hugging Face Docker Space for Bridges to Flow (synthetic data only).
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Spaces run the container as user ID 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Settings are passed as flags so the app works even if the hidden .streamlit folder isn't uploaded.
ENTRYPOINT ["streamlit", "run", "app.py", \
  "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", \
  "--browser.gatherUsageStats=false", "--client.toolbarMode=viewer", \
  "--theme.base=light", "--theme.primaryColor=#2b6cb0"]
