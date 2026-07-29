FROM python:3.11-slim

# Hugging Face Spaces require running as a non-root user
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install dependencies first (caching optimization)
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY --chown=user . .

# Hugging Face exposes port 7860 by default for web apps
ENV PORT=7860
EXPOSE 7860

# Start the bot
CMD ["python", "bot.py"]
