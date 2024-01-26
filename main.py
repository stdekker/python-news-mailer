import os
import requests
import json
import smtplib
import time

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def load_config(filename):
    with open(filename, "r") as f:
        return json.load(f)

def extract_links_from_article_tags(url, tag_class):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    links = []

    for article_tag in soup.find_all("article", class_=tag_class):
        a_tag = article_tag.find("a")
        if a_tag:
            link = a_tag.get("href")
            if link:
                absolute_link = urljoin(url, link)
                links.append(absolute_link)

    return links

def extract_info_from_article(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    title_element = soup.select_one("h1")
    time_element = soup.select_one("time")
    first_paragraph_element = soup.select_one("article p")

    if title_element:
        title = title_element.text.strip()
    else:
        print("Error: Title not found in the article.")
        return None

    time = time_element.text.strip() if time_element else "Time not available"
    first_paragraph = first_paragraph_element.text.strip() if first_paragraph_element else "First paragraph not available"

    return {
        "title": title,
        "time": time,
        "first_paragraph": first_paragraph,
        "url": url
    }

def save_links_to_file(filename, links):
    with open(filename, "w") as file:
        file.write("\n".join(links))

def compare_and_output_new_links(filename, new_links):
    if os.path.isfile(filename):
        with open(filename, "r") as file:
            existing_links = file.read().splitlines()

        new_links_set = set(new_links)
        existing_links_set = set(existing_links)
        new_links_set.difference_update(existing_links_set)

        if new_links_set:
            print("New links found:")
            for link in new_links_set:
                print(link)
            return new_links_set
        else:
            print("No new links found.")
            return set()
    else:
        print("No previous links file found.")
        print("New links found:")
        for link in new_links:
            print(link)
        return set(new_links)

def send_email(sender_name, sender_email, sender_password, recipients, subject, message, sender_login, delay=10):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"{sender_name} <{sender_email}>"
    html_message = MIMEText(message, 'html')
    msg.attach(html_message)

    try:
        with smtplib.SMTP('smtp.sp.nl', 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_login, sender_password)
            for recipient_email in recipients:
                msg['To'] = recipient_email
                server.sendmail(sender_email, recipient_email, msg.as_string())
                print(f"Email sent successfully to {recipient_email}!")
                time.sleep(delay)  # Throttling
    except smtplib.SMTPAuthenticationError:
        print("Error: Incorrect email credentials. Failed to send email.")
    except Exception as e:
        print(f"Error: Failed to send email. {e}")

if __name__ == "__main__":
    config = load_config("config.json")
    url = config["url"]
    tag_class = config["tag_class"]
    links_filename = config["links_filename"]
    email_name = config["email_name"]
    email_sender = config["email_sender"]
    email_password = config["email_password"]
    email_recipients = config["email_recipients"]
    email_login = config["email_login"]

    extracted_links = extract_links_from_article_tags(url, tag_class)
    email_subject = config["email_subject"]

    if extracted_links:
        new_links = compare_and_output_new_links(links_filename, extracted_links)
        if new_links:
            email_message = ""
            for link in new_links:
                info = extract_info_from_article(link)
                if info:
                    email_message += f"<h1>{info['title']}</h1>"
                    email_message += f"<p><strong>Op:</strong> {info['time']}</p>"
                    email_message += f"<p><strong>Intro:</strong> {info['first_paragraph']}</p>"
                    email_message += f"<p><a href='{info['url']}'>Lees meer</a></p>"

            send_email(email_name, email_sender, email_password, email_recipients, email_subject, email_message, email_login)
            save_links_to_file(links_filename, extracted_links)

        else:
            email_message = "<p>No new links found.</p>"
            email_subject = "Geen niews vandaag."
	    #send_email(email_sender, email_password, email_receiver, email_subject, email_message, email_login)
    else:
        email_message = "<p>No links found on the page.</p>"
        #send_email(email_sender, email_password, email_receiver, email_subject, email_message, email_login)
        print("Error: No links found on specified URL!")
