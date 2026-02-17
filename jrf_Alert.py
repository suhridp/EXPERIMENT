import requests
from bs4 import BeautifulSoup
import pdfplumber
import smtplib
import hashlib
import os
import logging
from urllib.parse import urljoin

# -------------------------
# CONFIG
# -------------------------
URLS = {
    "IIT Madras": "https://icandsr.iitm.ac.in/recruitment/",
    "IISC":"https://iisc.ac.in/careers/contractual-positions/",
    "IITG":"https://www.iitg.ac.in/iitg_reqr?ct=RzNJNURKa005enFYa3RJWWtvM2cvQT09"
    "IITB":"https://ep.iitb.ac.in/jobsearch#",
    "IITK":"https://www.iitk.ac.in/dord/scientific-and-research-staff",
    "IITD":"https://ird.iitd.ac.in/current-openings"
    }

KEYWORDS = ["JRF", "Junior Research Fellow"]

EMAIL = "your_email@gmail.com"
PASSWORD = "your_app_password"

DOWNLOAD_FOLDER = "pdfs"
SEEN_FILE = "seen.txt"

# -------------------------
# LOGGING
# -------------------------
logging.basicConfig(
    filename="jrf_agent.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -------------------------
# SETUP
# -------------------------
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r") as f:
        return set(f.read().splitlines())

def save_seen(hash_value):
    with open(SEEN_FILE, "a") as f:
        f.write(hash_value + "\n")

# -------------------------
# EMAIL
# -------------------------
def send_email(subject, body):
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        message = f"Subject: {subject}\n\n{body}"
        server.sendmail(EMAIL, EMAIL, message)
        server.quit()
        logging.info("Email sent successfully.")
    except Exception as e:
        logging.error(f"Email error: {e}")

# -------------------------
# PDF EXTRACT
# -------------------------
def extract_pdf_text(file_path):
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        logging.error(f"PDF extraction error: {e}")
    return text

# -------------------------
# MAIN
# -------------------------
def check_sites():
    seen = load_seen()

    for name, url in URLS.items():
        try:
            response = requests.get(url, timeout=15)
            soup = BeautifulSoup(response.text, "html.parser")

            for link in soup.find_all("a", href=True):
                href = link["href"]

                if ".pdf" in href.lower():
                    pdf_url = urljoin(url, href)
                    pdf_hash = hashlib.md5(pdf_url.encode()).hexdigest()

                    if pdf_hash in seen:
                        continue

                    logging.info(f"New PDF found: {pdf_url}")

                    pdf_response = requests.get(pdf_url, timeout=15)
                    file_path = os.path.join(DOWNLOAD_FOLDER, pdf_hash + ".pdf")

                    with open(file_path, "wb") as f:
                        f.write(pdf_response.content)

                    text = extract_pdf_text(file_path)

                    for keyword in KEYWORDS:
                        if keyword.lower() in text.lower():
                            subject = f"JRF PDF Found at {name}"
                            body = f"Keyword '{keyword}' found\n\nLink: {pdf_url}"
                            send_email(subject, body)
                            break

                    save_seen(pdf_hash)

        except Exception as e:
            logging.error(f"Error checking {name}: {e}")

if __name__ == "__main__":
    logging.info("Starting JRF Agent run...")
    check_sites()
    logging.info("Run completed.")
