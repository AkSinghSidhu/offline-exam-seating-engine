import pandas as pd
import os

def generate_templates():
    os.makedirs('templates', exist_ok=True)
    
    # Students template
    students_data = {
        'Date': ['15-05-2026', '15-05-2026'],
        'Roll No.': ['1001', '1002'],
        'Class': ['Class A', 'Class A'],
        'Sem': ['1', '1'],
        'Subject': ['Mathematics', 'Physics']
    }
    pd.DataFrame(students_data).to_excel('templates/template_students.xlsx', index=False)
    
    # Rooms template
    rooms_data = {
        'Floor': ['1st', '1st'],
        'Room': ['A-101', 'A-102'],
        'Col': [4, 4],
        'Row': [6, 5],
        'Total': [24, 20]
    }
    pd.DataFrame(rooms_data).to_excel('templates/template_rooms.xlsx', index=False)

if __name__ == "__main__":
    generate_templates()
    print("Templates generated successfully in the 'templates/' directory.")
