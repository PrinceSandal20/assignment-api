import requests
from bs4 import BeautifulSoup
import sqlite3
from flask import Flask, request, jsonify

#creating new flask application instance
app = Flask(__name__)

#scraping job data from the site
def scrape():
    base_url = "https://jobs.lever.co/MBRDNA"
    response = requests.get(base_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        job_listings = soup.find_all("div", class_="posting")
        job_data = []
        for job in job_listings:
            title = job.find("h5").text.strip()
            location = job.find("span", class_="sort-by-location").text.strip()
            link = base_url + job.find("a")["href"]
            job_data.append({"title": title, "location": location, "link": link, "type": "Intern", "company": "MBRDNA"})
        return job_data
    else:
        return None

#store data in local sqlite database
def store_data_in_db(job_data):
    conn = sqlite3.connect("job_database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS jobs
                 (title TEXT, location TEXT, link TEXT PRIMARY KEY, type TEXT, company TEXT)''')

    for job in job_data:
        try:
            c.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?)",
                      (job["title"], job["location"], job["link"], job["type"], job["company"]))
        except sqlite3.IntegrityError:
            # Skip if the job with the same link already exists in the database
            pass

    conn.commit()
    conn.close()

# API to run the scraper and store data in the database
@app.route("/api/scrape", methods=["GET"])
def scrape_and_store():
    site_filter = request.args.get("site", None)
    if site_filter is None or site_filter == "lever":
        job_data = scrape()
        if job_data:
            store_data_in_db(job_data)
            return jsonify({"message": "Scraping and storage successful!"}), 200
        else:
            return jsonify({"error": "Failed to scrape Lever site"}), 500
    else:
        return jsonify({"error": "Invalid site filter"}), 400

# API to retrieve job data from the database with filters
@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    conn = sqlite3.connect("job_database.db")
    c = conn.cursor()

    company_filter = request.args.get("company", None)
    job_type_filter = request.args.get("type", None)

    query = "SELECT * FROM jobs"
    conditions = []

    if company_filter:
        conditions.append(f"company = '{company_filter}'")

    if job_type_filter:
        conditions.append(f"type = '{job_type_filter}'")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " LIMIT 10;"

    c.execute(query)
    results = c.fetchall()
    conn.close()

    job_list = []
    for job in results:
        job_list.append({"title": job[0], "location": job[1], "link": job[2], "type": job[3], "company": job[4]})

    return jsonify(job_list), 200

if __name__ == "__main__":
    app.run(debug=True)
