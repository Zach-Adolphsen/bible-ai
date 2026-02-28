import os
import pandas as pd
import psycopg2
import requests
import re
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer

BASE_URL: str = "https://bible.helloao.org/api"
TRANSLATION_ID: str = "eng_kjv"


def call_complete_api(translation: str = TRANSLATION_ID):
    url = f"{BASE_URL}/{translation}/complete.json"
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
    rows = []
    df = pd.DataFrame()

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

                        rows.append({'book': book_name, 'chapter_num': chapter_num, "verse_num": verse_num, 'verse_text': verse_text, 'translation': translation})

        df = pd.DataFrame(rows)
        return df
    except Exception as e:
        print(f"Failed on book: {book_name}")
        print(f"Failed on chapter: {chapter_num}")
        print(f"Failed on verse: {verse_num}")
        print(f"Error loading data into DataFrame: {e}")
        print(df)
        exit(1)

def clean_data(df):
    df["book"] = df["book"].str.strip().astype(str)
    df["chapter_num"] = df["chapter_num"].astype(int)
    df["verse_num"] = df["verse_num"].astype(int)
    df["verse_text"] = (df["verse_text"]
                        .str.replace(r'[\n\r\t\f\v]+', ' ', regex=True)
                        .str.replace(r'\s+', ' ', regex=True)
                        .str.replace(r'([,.;:!?])\s*', r'\1 ', regex=True)
                        .str.strip()
                        .astype(str)
                        )
    df["translation"] = df["translation"].str.strip().astype(str)

def generate_embeddings(df):
    model = SentenceTransformer('all-MiniLM-L6-v2')

    texts = df["verse_text"].astype(str).tolist()
    embeddings = model.encode(texts, show_progress_bar=True)

    df["verse_embedding"] = embeddings.tolist()

def insert_data_to_db(df):
    try:
        load_dotenv()
        db_url = os.getenv("NEON_DB_URL")
        with psycopg2.connect(db_url) as conn:
            print("Connected to database")
            with conn.cursor() as cur:

                # Insert translation
                translation = df["translation"].unique()[0]
                print(f"Inserting data for translation: {translation}")
                translation_id = insert_translation(conn)

                book_names = df["book"].unique()
                for book_name in book_names:
                    cur.execute("SELECT id FROM books WHERE book_name = %s", (book_name,))
                    result = cur.fetchone()
                    if result is None:
                        print(f"Adding missing book to database: {book_name}")
                        cur.execute("INSERT INTO books (book_name) VALUES (%s) RETURNING id", (book_name,))
                        conn.commit()

                execute_values(cur, "SELECT id, book_name FROM books WHERE book_name IN %s", (book_names,))
                book_mapping = {book_name: book_id for book_id, book_name in cur.fetchall()}

                df["book_id"] = df["book"].map(book_mapping)
                print(f"Book mapping: {book_mapping}")
                print(df["book_id"].unique())
                df = df.drop(columns=["translation", "book"])

                row_data = [(
                    int(row["book_id"]),
                    int(row["chapter_num"]),
                    row["verse_num"],
                    row["verse_text"],
                    int(translation_id),
                    row["verse_embedding"]
                )
                    for _, row in df.iterrows()
                ]
                execute_values(cur,
                               "INSERT INTO verses (book_id, chapter_num, verse_num, verse_text, translation_id, verse_embedding) VALUES %s",
                               row_data
                )

                conn.commit()
                print("Inserted data into database")
    except Exception as e:
        print(f"Error inserting data into database: {e}")
        print(e.with_traceback())

def insert_translation(conn, translation: str = TRANSLATION_ID.strip()):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM translations WHERE translation_shortname = %s", [(translation,)])
        check_entry = cur.fetchone()

        if not check_entry:
            print(f"Adding new translation: {translation}")
            cur.execute("INSERT INTO translations (translation_shortname, translation_type) VALUES (%s, %s) RETURNING id", (translation, "mixed"))
            translation_id = cur.fetchone()[0]
            return translation_id
        else:
            return check_entry[0]
    

if __name__ == "__main__":
    # Get the API JSON data (the whole bible with footnotes)
    raw_data = call_complete_api()

    pd_data = get_book_data(raw_data)

    clean_data(pd_data)
    print(f"# of null entries per column (should all be 0):\n{pd_data.isnull().sum()}\n")
    print(f"Data Types:\n{pd_data.dtypes}")

    generate_embeddings(pd_data)

    insert_data_to_db(pd_data)
