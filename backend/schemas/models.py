from sqlmodel import Field, SQLModel


class Translation(SQLModel, table=True):
    __tablename__ = "translations"
    id: int | None = Field(default=None, primary_key=True)
    translation_shortname: str | None = Field(default=None)
    year_written_in: int | None = Field(default=None)
    translation_type: str | None = Field(default=None)


class Book(SQLModel, table=True):
    __tablename__ = "books"
    id: int | None = Field(default=None, primary_key=True)
    book_name: str | None = Field(default=None)
    testament: str | None = Field(default=None)


class Verse(SQLModel, table=True):
    __tablename__ = "verses"
    id: int | None = Field(default=None, primary_key=True)
    book_id: int | None = Field(default=None, foreign_key="books.id")
    translation_id: int | None = Field(default=None, foreign_key="translations.id")
    chapter_num: int | None = Field(default=None)
    verse_num: int | None = Field(default=None)
    verse_text: str | None = Field(default=None)
