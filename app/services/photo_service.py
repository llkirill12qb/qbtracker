from pathlib import Path
import shutil
import uuid
from PIL import Image


# базовая папка для всех загрузок
BASE_UPLOAD_DIR = Path("uploads/companies")


def get_employee_upload_dir(company_id: int) -> Path:
    """
    Создает папку для сотрудников компании:
    uploads/companies/company_<id>/employees/
    """
    path = BASE_UPLOAD_DIR / f"company_{company_id}" / "employees"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_employee_photo(upload_file, company_id: int, employee_id: int | None = None) -> str:
    """
    Сохраняет и оптимизирует фото сотрудника
    """

    employee_dir = get_employee_upload_dir(company_id)

    # имя файла
    if employee_id:
        filename = f"{employee_id}_photo.jpg"
    else:
        filename = f"{uuid.uuid4().hex}_photo.jpg"

    file_path = employee_dir / filename

    # обработка изображения
    image = Image.open(upload_file.file)
    image = image.convert("RGB")

    # уменьшаем размер (макс 400x400)
    image.thumbnail((400, 400))

    # сохраняем с сжатием
    image.save(
        file_path,
        format="JPEG",
        quality=85,
        optimize=True
    )

    # возвращаем путь для фронта (с прямыми слешами)
    return str(file_path).replace("\\", "/")


def delete_employee_photo(photo_filename: str | None, company_id: int) -> None:
    if not photo_filename:
        return

    file_path = get_employee_upload_dir(company_id) / photo_filename
    if file_path.exists():
        file_path.unlink()


def delete_company_upload_dir(company_id: int) -> None:
    company_dir = BASE_UPLOAD_DIR / f"company_{company_id}"
    if company_dir.exists():
        shutil.rmtree(company_dir)
