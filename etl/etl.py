import os
import pandas
import psycopg2
import requests
import re
from flask.cli import load_dotenv
from psycopg2.extras import execute_values

BASE_URL: str = "https://bible.helloao.org/api"
TRANSLATION_ID: str = "eng_kjv"

# BOOK_ABBREVIATIONS = {
#     "Genesis": "GEN",
#     "Exodus": "EXO",
#     "Leviticus": "LEV",
#     "Numbers": "NUM",
#     "Deuteronomy": "DEU",
#     "Joshua": "JOS",
#     "Judges": "JDG",
#     "Ruth": "RUT",
#     "1 Samuel": "1SA",
#     "2 Samuel": "2SA",
#     "1 Kings": "1KI",
#     "2 Kings": "2KI",
#     "1 Chronicles": "1CH",
#     "2 Chronicles": "2CH",
#     "Ezra": "EZR",
#     "Nehemiah": "NEH",
#     "Esther": "EST",
#     "Job": "JOB",
#     "Psalms": "PSA",
#     "Proverbs": "PRO",
#     "Ecclesiastes": "ECC",
#     "Song of Solomon": "SNG",
#     "Isaiah": "ISA",
#     "Jeremiah": "JER",
#     "Lamentations": "LAM",
#     "Ezekiel": "EZK",
#     "Daniel": "DAN",
#     "Hosea": "HOS",
#     "Joel": "JOL",
#     "Amos": "AMO",
#     "Obadiah": "OBA",
#     "Jonah": "JON",
#     "Micah": "MIC",
#     "Nahum": "NAM",
#     "Habakkuk": "HAB",
#     "Zephaniah": "ZEP",
#     "Haggai": "HAG",
#     "Zechariah": "ZEC",
#     "Malachi": "MAL",
#     "Matthew": "MAT",
#     "Mark": "MRK",
#     "Luke": "LUK",
#     "John": "JHN",
#     "Acts": "ACT",
#     "Romans": "ROM",
#     "1 Corinthians": "1CO",
#     "2 Corinthians": "2CO",
#     "Galatians": "GAL",
#     "Ephesians": "EPH",
#     "Philippians": "PHP",
#     "Colossians": "COL",
#     "1 Thessalonians": "1TH",
#     "2 Thessalonians": "2TH",
#     "1 Timothy": "1TI",
#     "2 Timothy": "2TI",
#     "Titus": "TIT",
#     "Philemon": "PHM",
#     "Hebrews": "HEB",
#     "James": "JAS",
#     "1 Peter": "1PE",
#     "2 Peter": "2PE",
#     "1 John": "1JN",
#     "2 John": "2JN",
#     "3 John": "3JN",
#     "Jude": "JUD",
#     "Revelation": "REV"
# }

def call_complete_api(translation_id: str):
    url = f"{BASE_URL}/{translation_id}/complete.json"
    print(url)
    data = requests.get(url)

    return data.json()

def get_verse_text(verse):
    text = ""

    # Search through all content items to find text elements
    for content in verse["content"]:
        if isinstance(content, str):
            text += content
        elif isinstance(content, dict):
            if "text" in content:
                text += content["text"]

    if isinstance(text, str):
        # Remove all line breaks, tabs, and other whitespace characters
        text = re.sub(r'[\n\r\t\f\v]', ' ', text)
        # Keep only letters, numbers, spaces, and basic punctuation
        text = re.sub(r'[^a-zA-Z0-9\s.,;:!?\'"()-]', '', text)
        # Replace multiple spaces with single-space
        text = re.sub(r'\s+', ' ', text)
        # Trim whitespace from beginning and end
        text = text.strip()

    return text

def get_book_data(data):
    df = pandas.DataFrame()

    translation = data["translation"]["shortName"]

    try:
        for book in data["books"]:
            book_name: str = book["name"]

            for chapter in book["chapters"]:
                chapter_num: int = chapter["chapter"]["number"]
                for verse in chapter["chapter"]["content"]:
                    if verse["type"] == "verse":
                        verse_num: int = verse["number"]
                        verse_text: str = get_verse_text(verse)

                        df = df._append({'book': book_name, 'chapter_num': chapter_num, "verse_num": verse_num, 'verse_text': verse_text, 'translation': translation}, ignore_index=True)


        return df
    except Exception as e:
        print(f"Failed on book: {book_name}")
        print(f"Failed on chapter: {chapter_num}")
        print(f"Failed on verse: {verse_num}")
        print(f"Error loading data into DataFrame: {e}")

def clean_data(df):
    df["book"] = df["book"].str.strip().astype(str)
    df["chapter_num"] = df["chapter_num"].astype(int)
    df["verse_num"] = df["verse_num"].astype(int)
    df["verse_text"] = df["verse_text"].str.replace(r'[\n\r\t\f\v]+', ' ', regex=True).str.replace(r'\s+', ' ', regex=True).str.strip().astype(str)
    df["translation"] = df["translation"].str.strip().astype(str)

def insert_data_to_db(df):
    try:
        load_dotenv()
        db_url = os.getenv("NEON_DB_URL")
        with psycopg2.connect(db_url) as conn:
            print("Connected to database")
            with conn.cursor() as cur:

                row_data = [tuple(row) for row in df.values]
                execute_values(cur,
                               "INSERT INTO bible_verses (book, chapter_num, verse_num, verse_text, translation) VALUES %s",
                               row_data
                )

                conn.commit()
                print("Inserted data into database")
    except Exception as e:
        print(f"Error inserting data into database: {e}")
    

if __name__ == "__main__":
    # Get the API JSON data (the whole KJV bible with footnotes)
    raw_data = call_complete_api(TRANSLATION_ID)

    pd_data = get_book_data(raw_data)

    clean_data(pd_data)
    # print(f"# of null entries per column (should all be 0):\n{pd_data.isnull().sum()}\n")
    # print(f"Data Types:\n{pd_data.dtypes}")

    insert_data_to_db(pd_data)
