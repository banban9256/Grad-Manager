import csv
import re

def parse_schedules(schedule_str):
    pattern = r'([월화수목금토일])\((\d{2}:\d{2})~(\d{2}:\d{2})\)'
    matches = re.findall(pattern, schedule_str)
    return matches

def main():
    csv_path = 'data/input_data/26전체강의목록.csv'
    
    unparsed_samples = []
    parsed_count = 0
    unparsed_count = 0
    total_count = 0
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_count += 1
            sched_str = row.get('강의시간', '').strip()
            
            # 비어 있는 강의시간 제외
            if not sched_str:
                unparsed_count += 1
                continue
                
            matches = parse_schedules(sched_str)
            if not matches:
                unparsed_count += 1
                if len(unparsed_samples) < 20:
                    unparsed_samples.append((row['학수번호'], row['교과목명'], sched_str))
            else:
                parsed_count += 1
                
    print(f"총 행 수: {total_count}")
    print(f"파싱 성공 행 수: {parsed_count}")
    print(f"파싱 실패 행 수 (시간표가 비었거나 정규식 불일치): {unparsed_count}")
    print("\n파싱 실패 샘플 (상위 20개):")
    for item in unparsed_samples:
        print(f"학수번호: {item[0]}, 과목명: {item[1]}, 강의시간: '{item[2]}'")

if __name__ == '__main__':
    main()
