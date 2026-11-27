import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

# students.json is the "memory"; it is saved next to this script.
DEFAULT_DATA_FILE = Path(__file__).with_name("students.json")

GPA_MIN = 1.0
GPA_MAX = 5.0


class RecordError(Exception):
    """Raised for any invalid input or failed record action."""


@dataclass
class Student:
    student_id: str
    name: str
    gpa: float

    def __str__(self) -> str:
        return f"{self.student_id:<12} {self.name:<30} {self.gpa:.2f}"


def clean_id(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise RecordError("Student ID cannot be empty.")
    if re.search(r"\s", value):
        raise RecordError("Student ID cannot contain spaces.")
    return value


def clean_name(value: str) -> str:
    value = " ".join((value or "").split())
    if not value:
        raise RecordError("Name cannot be empty.")
    return value


def clean_gpa(value) -> float:
    try:
        gpa = float(str(value).strip())
    except (TypeError, ValueError):
        raise RecordError(
            f"GPA must be a number between {GPA_MIN:.1f} and {GPA_MAX:.1f}."
        ) from None
    if gpa != gpa or not (GPA_MIN <= gpa <= GPA_MAX):
        raise RecordError(
            f"GPA must be between {GPA_MIN:.1f} and {GPA_MAX:.1f}."
        )
    return round(gpa, 2)


def _natural_key(text: str):
    # Sorts "2" before "10" instead of "10" before "2".
    return [
        (0, int(part), "") if part.isdigit() else (1, 0, part.lower())
        for part in re.split(r"(\d+)", text)
        if part != ""
    ]


class StudentRecords:
    def __init__(self, data_file=None):
        self._students: dict[str, Student] = {}
        self.data_file = Path(data_file) if data_file else None
        if self.data_file and self.data_file.exists():
            self._load()

    def _load(self) -> None:
        try:
            text = self.data_file.read_text(encoding="utf-8").strip()
            raw = json.loads(text) if text else []
            for item in raw:
                s = Student(
                    clean_id(item["student_id"]),
                    clean_name(item["name"]),
                    clean_gpa(item["gpa"]),
                )
                self._students[s.student_id] = s
        except (OSError, ValueError, KeyError, TypeError, RecordError):
            raise RecordError(
                f"Could not read '{self.data_file}'. The file may be damaged. "
                "Fix or delete it and try again."
            ) from None

    def save(self) -> None:
        if not self.data_file:
            return
        data = [asdict(s) for s in self._students.values()]
        tmp = self.data_file.with_suffix(self.data_file.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.data_file)

    def __len__(self) -> int:
        return len(self._students)

    def add(self, student_id, name, gpa) -> Student:
        sid = clean_id(student_id)
        if sid in self._students:
            raise RecordError(f"Student ID '{sid}' is already in use.")
        student = Student(sid, clean_name(name), clean_gpa(gpa))
        self._students[sid] = student
        self.save()
        return student

    def get(self, student_id) -> Student:
        sid = (student_id or "").strip()
        if sid not in self._students:
            raise RecordError(f"No student found with ID '{sid}'.")
        return self._students[sid]

    def update(self, student_id, *, new_id=None, name=None, gpa=None) -> Student:
        student = self.get(student_id)
        new_name = clean_name(name) if name is not None else student.name
        new_gpa = clean_gpa(gpa) if gpa is not None else student.gpa
        target_id = clean_id(new_id) if new_id is not None else student.student_id
        if target_id != student.student_id and target_id in self._students:
            raise RecordError(f"Student ID '{target_id}' is already in use.")

        del self._students[student.student_id]
        student.student_id, student.name, student.gpa = target_id, new_name, new_gpa
        self._students[target_id] = student
        self.save()
        return student

    def remove(self, student_id) -> Student:
        student = self.get(student_id)
        del self._students[student.student_id]
        self.save()
        return student

    def list_by_id(self) -> list[Student]:
        return sorted(self._students.values(), key=lambda s: _natural_key(s.student_id))

    def sort_by_gpa(self, descending=True) -> list[Student]:
        return sorted(self.list_by_id(), key=lambda s: -s.gpa if descending else s.gpa)

    def sort_by_name(self) -> list[Student]:
        return sorted(self.list_by_id(), key=lambda s: s.name.casefold())

    def find_by_name(self, name) -> list[Student]:
        wanted = clean_name(name).casefold()
        return [s for s in self.list_by_id() if s.name.casefold() == wanted]


MENU = """

STUDENT RECORD MANAGEMENT SYSTEM

(1) Add a Student
(2) View a Student by ID
(3) Update a Student
(4) Remove a Student
(5) List all Students (by ID)
(6) Sort by GPA
(7) Sort by Name
(8) Find by Name
(0) Exit
"""


# actions
def show_table(students, title) -> None:
    print(f"\n{title}")
    if not students:
        print("  (no records)")
        return
    print(f"{'ID':<12} {'NAME':<30} GPA")
    print("-" * 48)
    for s in students:
        print(s)
    print(f"\nTotal: {len(students)}")


def action_add(db: StudentRecords) -> None:
    sid = input("Student ID: ")
    name = input("Name: ")
    gpa = input(f"GPA ({GPA_MIN:.1f}-{GPA_MAX:.1f}): ")
    student = db.add(sid, name, gpa)
    print(f"\nAdded: {student}")


def action_view(db: StudentRecords) -> None:
    student = db.get(input("Student ID: "))
    show_table([student], "Student record")


def action_update(db: StudentRecords) -> None:
    student = db.get(input("Student ID to update: "))
    print(f"Current: {student}")
    print("(Press Enter to keep the current value.)")
    new_id = input("New ID: ").strip() or None
    name = input("New name: ").strip() or None
    gpa = input("New GPA: ").strip() or None
    updated = db.update(student.student_id, new_id=new_id, name=name, gpa=gpa)
    print(f"\nUpdated: {updated}")


def action_remove(db: StudentRecords) -> None:
    student = db.get(input("Student ID to remove: "))
    print(f"Record: {student}")
    if input("Remove this student? (y/n): ").strip().lower() == "y":
        db.remove(student.student_id)
        print("\nRecord removed.")
    else:
        print("\nCancelled. Nothing was removed.")


def action_list(db: StudentRecords) -> None:
    show_table(db.list_by_id(), "All students (ascending by ID)")


def action_sort_gpa(db: StudentRecords) -> None:
    show_table(db.sort_by_gpa(), "Students by GPA (highest to lowest; ties by ID)")


def action_sort_name(db: StudentRecords) -> None:
    show_table(db.sort_by_name(), "Students by name (A to Z; ties by ID)")


def action_find(db: StudentRecords) -> None:
    name = input("Name to search: ")
    matches = db.find_by_name(name)
    if not matches:
        raise RecordError(f"No student found with the name '{clean_name(name)}'.")
    show_table(matches, f"Matches for '{clean_name(name)}'")


ACTIONS = {
    "1": action_add,
    "2": action_view,
    "3": action_update,
    "4": action_remove,
    "5": action_list,
    "6": action_sort_gpa,
    "7": action_sort_name,
    "8": action_find,
}


# main
def main() -> None:
    try:
        db = StudentRecords(DEFAULT_DATA_FILE)
    except RecordError as err:
        print(f"Error: {err}")
        return

    print(f"Loaded {len(db)} record(s) from {DEFAULT_DATA_FILE.name}.")

    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Thank you!")
            break

        action = ACTIONS.get(choice)
        if action is None:
            print("Invalid choice. Please enter a number from 0 to 8.")
            continue

        try:
            action(db)
        except RecordError as err:
            print(f"\nError: {err}")
        except OSError:
            print(f"\nError: Could not save to {DEFAULT_DATA_FILE.name}.")
        
        input("\nPress Enter to return to the menu.")


if __name__ == "__main__":
    main()