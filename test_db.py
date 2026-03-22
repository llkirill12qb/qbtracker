from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:12345678@localhost:5432/employee_tracker"

engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("Подключение к PostgreSQL успешно!")
        print("Результат:", result.scalar())
except Exception as e:
    print("Ошибка подключения:")
    print(e)