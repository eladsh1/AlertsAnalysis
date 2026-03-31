# AlertsAnalysis

אפליקציית Streamlit לטעינה וניתוח נתוני אזעקות.

## הרצה מקומית

1. התקנת תלויות:

	```bash
	pip install -r requirements.txt
	```

2. הרצה:

	```bash
	streamlit run main.py
	```

## פריסה ל-Streamlit Cloud

האפליקציה הותאמה לפריסה בענן:

- נתיב נתוני JSON נטען ממשתנה סביבה `RAW_DATA_PATH`.
- אם המשתנה לא מוגדר, ברירת המחדל היא `RawData` מתוך הריפו.
- נתיב SQLite נטען ממשתנה סביבה `DB_PATH`.
- אם המשתנה לא מוגדר, ברירת המחדל היא קובץ זמני במערכת (`temp`), מתאים לסביבת ענן.

### הגדרות מומלצות ב-Streamlit Cloud

במסך Secrets / Variables אפשר להגדיר:

- `RAW_DATA_PATH` = `RawData`
- `DB_PATH` = `/tmp/alerts_analysis.db`

### חשוב לדעת

- אחסון קבצים מקומי בענן הוא זמני. קובץ ה-DB עלול להימחק בריסטארט/פריסה מחדש.
- אם צריך התמדה מלאה, מומלץ להעביר את הלוגים והנתונים למסד נתונים חיצוני.
