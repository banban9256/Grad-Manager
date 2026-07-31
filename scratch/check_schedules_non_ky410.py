import csv
import re

def parse_schedules(schedule_str):
    pattern = r'([월화수목금토일])\((\d{2}:\d{2})~(\d{2}:\d{2})\)'
    matches = re.findall(pattern, schedule_str)
    return matches

def main():
    csv_path = 'data/input_data/26전체강의목록.csv'
    
    unparsed_samples = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code_parts = row['학수번호'].split('-')
            code_raw = code_parts[0]
            
            # KY410 (진로와상담)은 제외하고 분석
            if code_raw == 'KY410':
                continue
                
            sched_str = row.get('강의시간', '').strip()
            
            # 비어있지 않고 '-' 도 아닌데 매칭이 안 되는 경우 찾기
            if sched_str and sched_str != '-':
                matches = parse_schedules(sched_str)
                if not matches:
                    if len(unparsed_samples) < 30:
                        unparsed_samples.append((row['학수번호'], row['교과목명'], sched_str))
                        
    print("\nKY410 제외 파싱 실패 샘플:")
    for item in unparsed_samples:
        print(f"학수번호: {item[0]}, 과목명: {item[1]}, 강의시간: '{item[2]}'")

if __name__ == '__main__':
    main()
