FROM python:3.12-slim

# Der Assistent läuft nicht als root, sondern als "assistent" (UID/GID 1000 – dieselbe UID,
# als die Asterisk im Image andrius/asterisk läuft). setpriv (util-linux), find und useradd
# gehören zum Debian-Grundsystem.
RUN groupadd --gid 1000 assistent \
    && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin assistent

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY assistent ./assistent
RUN python -m compileall -q assistent
COPY container-start.sh /usr/local/bin/container-start.sh
RUN chmod 755 /usr/local/bin/container-start.sh

# Startet als root, übergibt /daten bzw. /asterisk/etc an UID 1000 und wechselt dann den Benutzer.
ENTRYPOINT ["/usr/local/bin/container-start.sh"]
CMD ["python", "-m", "assistent"]
