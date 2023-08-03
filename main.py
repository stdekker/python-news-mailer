import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import smtplib
from email.mime.text import MIMEText
import json

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

    if title_element and time_element and first_paragraph_element:
        title = title_element.text.strip()
        time = time_element.text.strip()
        first_paragraph = first_paragraph_element.text.strip()

        return {
            "title": title,
            "time": time,
            "first_paragraph": first_paragraph,
            "url": url
        }
    else:
        print("Error: Some required elements not found in the article.")
        return None

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

def send_email(sender_email, sender_password, receiver_email, subject, message,sender_login):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    try:
        with smtplib.SMTP_SSL('email-smtp.eu-central-1.amazonaws.com', 465) as server:
            server.login(sender_login, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("Email sent successfully!")
    except smtplib.SMTPAuthenticationError:
        print("Error: Incorrect email credentials. Failed to send email.")
    except Exception as e:
        print(f"Error: Failed to send email. {e}")

if __name__ == "__main__":
    config = load_config("config.json")
    url = config["url"]
    tag_class = config["tag_class"]
    links_filename = config["links_filename"]
    email_sender = config["email_sender"]
    email_password = config["email_password"]
    email_receiver = config["email_receiver"]
    email_login = config["email_login"]

    extracted_links = extract_links_from_article_tags(url, tag_class)

    if extracted_links:
        new_links = compare_and_output_new_links(links_filename, extracted_links)
        if new_links:
            email_subject = config["email_subject"]
            email_message = ""
            for link in new_links:
                info = extract_info_from_article(link)
                if info:
                    email_message += f"{info['title']}\n"
                    email_message += f"Op: {info['time']}\n"
                    email_message += f"Intro: {info['first_paragraph']}\n"
                    email_message += f"Lees meer: {info['url']}\n"
                    email_message += "\n\n"

            send_email(email_sender, email_password, email_receiver, email_subject, email_message, email_login)
        save_links_to_file(links_filename, extracted_links)
    else:
        print("No links found.")
