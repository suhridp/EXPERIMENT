import requests
from bs4 import BeautifulSoup
import pdfplumber
import hashlib
import os
import logging
from urllib.parse import urljoin, urlparse

# -------------------------
# CONFIG
# -------------------------

IIT_ROOTS = {
    "IIT Bombay": [
        "https://www.iitb.ac.in/en/careers",
        "https://rnd.iitb.ac.in/jobs"
    ],
    "IIT Delhi": [
        "https://ird.iitd.ac.in/current-openings",
        "https://home.iitd.ac.in/jobs-iitd/index.php"
    ],
    "IIT Madras": [
        "https://icandsr.iitm.ac.in/recruitment/"
    ],
    "IIT Kanpur": [
        "https://www.iitk.ac.in/new/recruitment"
    ],
    "IIT Kharagpur": [
        "https://erp.iitkgp.ac.in/SricWeb/temporaryJobs.htm"
    ],
    "IIT Roorkee": [
        "https://iitr.ac.in/Careers/index.html"
    ],
}

KEYWORDS = ["JRF", "Junior Research Fellow", "Project Associate"]

MAX_DEPTH = 2
HASH_DB = "pdf_hashes.txt"
DOWNLOAD_DIR = "pdfs"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(
    filename="jrf_agent.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -------------------------
# HASH STORAGE
# -------------------------

def load_hashes():
    if not os.path.exists(HASH_DB):
        return set()
    with open(HASH_DB, "r") as f:
        return set(f.read().splitlines())

def save_hash(h):
    with open(HASH_DB, "a") as f:
        f.write(h + "\n")

def hash_content(content):
    return hashlib.sha256(content).hexdigest()

# -------------------------
# PDF TEXT EXTRACTION
# -------------------------

def extract_text(file_path):
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        logging.warning(f"PDF read error: {e}")
    return text

# -------------------------
# CONTROLLED CRAWLER
# -------------------------

def crawl_page(base_url, current_url, depth, visited, seen_hashes):

    if depth > MAX_DEPTH:
        return

    if current_url in visited:
        return

    visited.add(current_url)

    try:
        response = requests.get(current_url, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        logging.warning(f"Page fetch error: {current_url} | {e}")
        return

    for link in soup.find_all("a", href=True):

        full_url = urljoin(current_url, link["href"])
        parsed_base = urlparse(base_url).netloc
        parsed_link = urlparse(full_url).netloc

        # Stay within same domain
        if parsed_base not in parsed_link:
            continue

        # PDF detection
        if full_url.lower().endswith(".pdf"):
            process_pdf(full_url, seen_hashes)

        # Follow relevant pages only
        elif any(keyword in full_url.lower() for keyword in
                 ["recruit", "career", "project", "sponsored", "temporary"]):

            crawl_page(base_url, full_url, depth + 1, visited, seen_hashes)

# -------------------------
# PDF PROCESSOR
# -------------------------

def process_pdf(pdf_url, seen_hashes):

    try:
        pdf_response = requests.get(pdf_url, timeout=15)
        content_hash = hash_content(pdf_response.content)

        if content_hash in seen_hashes:
            return

        file_path = os.path.join(DOWNLOAD_DIR, content_hash + ".pdf")
        with open(file_path, "wb") as f:
            f.write(pdf_response.content)

        text = extract_text(file_path)

        if any(k.lower() in text.lower() for k in KEYWORDS):
            logging.info(f"NEW_JRF_FOUND: {pdf_url}")
            print(f"NEW JRF FOUND: {pdf_url}")

        save_hash(content_hash)

    except Exception as e:
        logging.warning(f"PDF processing error: {pdf_url} | {e}")

# -------------------------
# MAIN RUN
# -------------------------

if __name__ == "__main__":

    logging.info("Starting Hybrid IIT Scan")

    seen_hashes = load_hashes()

    for institute, roots in IIT_ROOTS.items():
        logging.info(f"Scanning {institute}")
        for root in roots:
            crawl_page(root, root, 0, set(), seen_hashes)

    logging.info("Scan Completed")
