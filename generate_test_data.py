import pandas as pd
import random
import os
import argparse

# Define proper courses and their subjects
COURSES = {
    "B.Tech CSE": {
        "odd": ["Data Structures", "Operating Systems", "Computer Networks", "Database Management", "Discrete Mathematics", "Software Engineering"],
        "even": ["Algorithms", "Machine Learning", "Computer Architecture", "Theory of Computation", "Compiler Design", "Artificial Intelligence"]
    },
    "B.Tech ECE": {
        "odd": ["Analog Electronics", "Digital Logic", "Signals and Systems", "Electromagnetic Theory", "Microprocessors"],
        "even": ["Communication Systems", "VLSI Design", "Digital Signal Processing", "Control Systems", "Antenna Theory"]
    },
    "B.Sc Physics": {
        "odd": ["Classical Mechanics", "Electromagnetism", "Mathematical Physics", "Thermal Physics"],
        "even": ["Quantum Mechanics", "Statistical Mechanics", "Solid State Physics", "Nuclear Physics"]
    },
    "B.A. English": {
        "odd": ["British Literature", "American Literature", "Literary Theory", "Linguistics"],
        "even": ["World Literature", "Victorian Literature", "Modern Poetry", "Drama"]
    },
    "B.Com": {
        "odd": ["Financial Accounting", "Business Law", "Economics", "Corporate Accounting"],
        "even": ["Cost Accounting", "Taxation", "Auditing", "Business Management"]
    },
    "BBA": {
        "odd": ["Principles of Management", "Business Economics", "Marketing Management", "Organizational Behavior"],
        "even": ["Financial Management", "Human Resource Management", "Business Ethics", "Strategic Management"]
    }
}

def get_student_count():
    """
    Returns student count based on the requested probability distribution:
    - 0-5: 10%
    - 6-10: 10%
    - 11-30: 35%
    - 31-40: 30%
    - 41-60: 15%
    """
    p = random.random()
    if p < 0.10:
        return random.randint(1, 5)
    elif p < 0.20:
        return random.randint(6, 10)
    elif p < 0.55:
        return random.randint(11, 30)
    elif p < 0.85:
        return random.randint(31, 40)
    else:
        return random.randint(41, 60)

def generate_data(target_students=1000, is_odd_sem=True, output_file="data/test_data.xlsx"):
    data = []
    
    sem_choices = [1, 3, 5, 7] if is_odd_sem else [2, 4, 6, 8]
    sem_type = "odd" if is_odd_sem else "even"
    
    used_combos = set()
    current_students = 0
    num_exams = 0
    
    while current_students < target_students:
        # Pick a random course
        course = random.choice(list(COURSES.keys()))
        
        # Pick a subject and semester
        subject = random.choice(COURSES[course][sem_type])
        sem = random.choice(sem_choices)
        
        # Ensure unique combo so exams don't accidentally merge
        combo = (course, sem, subject)
        attempts = 0
        while combo in used_combos and attempts < 100:
            course = random.choice(list(COURSES.keys()))
            subject = random.choice(COURSES[course][sem_type])
            sem = random.choice(sem_choices)
            combo = (course, sem, subject)
            attempts += 1
            
        used_combos.add(combo)
        
        num_students = get_student_count()
        
        # Generate realistic looking roll numbers
        year_prefix = str(2026 - (sem // 2))[-2:]  # E.g., "24" for 2nd year
        course_code = str(list(COURSES.keys()).index(course) + 1).zfill(2)
        base_roll = int(f"{year_prefix}{course_code}000")
        
        for i in range(num_students):
            data.append({
                "Roll No.": str(base_roll + i + 1),
                "Class": course,
                "Sem": sem,
                "Subject": subject
            })
            
        current_students += num_students
        num_exams += 1
            
    df = pd.DataFrame(data)
    
    # Sort the dataset properly by Class, Semester, Subject, and Roll Number
    df = df.sort_values(by=["Class", "Sem", "Subject", "Roll No."]).reset_index(drop=True)
    
    # Save to Excel
    df.to_excel(output_file, index=False)
    print(f"✅ Generated {len(df)} students across {num_exams} unique exams in '{output_file}'")
    print(f"✅ Semester Type: {'Odd' if is_odd_sem else 'Even'}\n")
    
    # Print stats
    stats = df.groupby(['Class', 'Sem', 'Subject']).size().reset_index(name='Student Count')
    print("--- Exam Breakdown ---")
    print(stats.to_string(index=False))
    print("-" * 22)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate test data for seating engine.")
    parser.add_argument("--students", type=int, default=None, help="Target number of students to generate")
    parser.add_argument("--even", action="store_true", help="Generate even semester data instead of odd (default is odd)")
    parser.add_argument("--output", type=str, default="data/generated_test_data.xlsx", help="Output file path")
    args = parser.parse_args()
    
    target_students = args.students
    if target_students is None:
        try:
            target_students = int(input("Enter the approximate number of students to generate (e.g. 1000): "))
        except ValueError:
            print("Invalid input. Defaulting to 1000 students.")
            target_students = 1000
    
    # Ensure directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    generate_data(target_students=target_students, is_odd_sem=not args.even, output_file=args.output)
