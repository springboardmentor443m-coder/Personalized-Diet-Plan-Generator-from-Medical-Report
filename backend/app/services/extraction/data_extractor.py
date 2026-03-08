import re
from datetime import datetime

class DataExtractor:
    def __init__(self):
        self.patterns = {}
        self.test_configs = {
            'glucose': {'aliases': ['fasting glucose', 'blood sugar', 'glucose'], 'valid_range': (40, 500), 'unit_hints': ['mg/dl', 'mmol/l']},
            'cholesterol_total': {'aliases': ['total cholesterol', 'cholesterol total', 'cholesterol'], 'valid_range': (80, 500), 'unit_hints': ['mg/dl']},
            'hdl': {'aliases': ['hdl cholesterol', 'hdl'], 'valid_range': (10, 150), 'unit_hints': ['mg/dl']},
            'ldl': {'aliases': ['ldl cholesterol', 'ldl'], 'valid_range': (20, 400), 'unit_hints': ['mg/dl']},
            'triglycerides': {'aliases': ['triglycerides', 'tg'], 'valid_range': (20, 1000), 'unit_hints': ['mg/dl']},
            'hba1c': {'aliases': ['hba1c', 'a1c', 'glycated hemoglobin'], 'valid_range': (3, 20), 'unit_hints': ['%']},
            'bmi': {'aliases': ['body mass index', 'bmi'], 'valid_range': (10, 60), 'unit_hints': []},
            'weight': {'aliases': ['weight', 'wt'], 'valid_range': (20, 300), 'unit_hints': ['kg']},
            'height': {'aliases': ['height', 'ht'], 'valid_range': (100, 230), 'unit_hints': ['cm']},
            'hemoglobin': {'aliases': ['hemoglobin', 'haemoglobin'], 'valid_range': (4, 22), 'unit_hints': ['g/dl']},
            'creatinine': {'aliases': ['creatinine'], 'valid_range': (0.2, 20), 'unit_hints': ['mg/dl']},
            'uric_acid': {'aliases': ['uric acid'], 'valid_range': (1, 20), 'unit_hints': ['mg/dl']},
        }
        self.noise_markers = [
            'reference range', 'ref. interval', 'interpretation', 'recommended when',
            'equation', 'kindly', 'within', 'hours', 'interlaboratory', 'variation'
        ]
        
        self.thresholds = {
            'glucose': {'normal': (70, 100), 'prediabetes': (100, 125), 'diabetes': (125, 300)},
            'cholesterol_total': {'normal': (0, 200), 'borderline': (200, 239), 'high': (240, 400)},
            'hdl': {'low': (0, 40), 'normal': (40, 60), 'high': (60, 100)},
            'ldl': {'optimal': (0, 100), 'near_optimal': (100, 129), 'borderline': (129, 159), 'high': (159, 400)},
            'triglycerides': {'normal': (0, 150), 'borderline': (150, 199), 'high': (200, 500)},
            'hba1c': {'normal': (0, 5.7), 'prediabetes': (5.7, 6.4), 'diabetes': (6.5, 15)},
            'bmi': {'underweight': (0, 18.5), 'normal': (18.5, 25), 'overweight': (25, 30), 'obese': (30, 50)},
            'bp_systolic': {'normal': (0, 120), 'elevated': (120, 130), 'hypertension': (130, 200)},
            'bp_diastolic': {'normal': (0, 80), 'elevated': (80, 90), 'hypertension': (90, 150)},
        }
    
    def extract_values(self, text):
        text_lower = text.lower()
        results = {}

        bp_match = re.search(r'\b(?:bp|blood pressure|b\.p\.)\b[^\n\r\d]{0,20}(\d{2,3})\s*/\s*(\d{2,3})', text_lower, re.IGNORECASE)
        if bp_match:
            systolic = float(bp_match.group(1))
            diastolic = float(bp_match.group(2))
            results['bp_systolic'] = {'value': systolic, 'status': self._check_threshold('bp_systolic', systolic)}
            results['bp_diastolic'] = {'value': diastolic, 'status': self._check_threshold('bp_diastolic', diastolic)}

        lines = [ln.strip() for ln in text_lower.splitlines() if ln.strip()]
        for key, config in self.test_configs.items():
            candidate = self._extract_metric_from_lines(lines, config)
            if candidate is None:
                continue
            results[key] = {
                'value': candidate,
                'status': self._check_threshold(key, candidate)
            }

        return results

    def _extract_metric_from_lines(self, lines, config):
        best_score = float('-inf')
        best_value = None

        for line in lines:
            if any(marker in line for marker in self.noise_markers):
                continue

            alias_hit = None
            for alias in config['aliases']:
                if alias in line:
                    alias_hit = alias
                    break
            if not alias_hit:
                continue

            numbers = list(re.finditer(r'(?<![\d/])(\d+(?:\.\d+)?)', line))
            if not numbers:
                continue

            alias_pos = line.find(alias_hit)
            for num_match in numbers:
                value = float(num_match.group(1))
                if not (config['valid_range'][0] <= value <= config['valid_range'][1]):
                    continue

                distance = abs(num_match.start() - alias_pos)
                score = 100 - distance

                if any(unit in line for unit in config['unit_hints']):
                    score += 15
                if line.startswith(alias_hit):
                    score += 10
                if re.search(r'\b\d+(\.\d+)?\s*-\s*\d+(\.\d+)?\b', line):
                    score -= 10
                if '<' in line or '>' in line:
                    score -= 12

                if score > best_score:
                    best_score = score
                    best_value = value

        return best_value
    
    def _check_threshold(self, test_name, value):
        if test_name not in self.thresholds:
            return 'unknown'
        
        ranges = self.thresholds[test_name]
        for status, (min_val, max_val) in ranges.items():
            if min_val <= value < max_val:
                return status
        return 'out_of_range'
    
    def extract_patient_info(self, text):
        info = {}
        
        name_patterns = [
            r'(?:patient\s*name|name\s*of\s*patient)[\s:]+([A-Z][A-Za-z\s]{2,40})(?:\n|\r|$)',
            r'(?:^|\n)name[\s:]+([A-Z][A-Za-z\s]{2,40})(?:\n|\r)',
            r'(?:mr\.|mrs\.|ms\.)[\s]+([A-Z][A-Za-z\s]{2,40})(?:\n|\r)',
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if name_match:
                name = name_match.group(1).strip()
                if name.lower() not in ['lab no', 'age', 'gender', 'test', 'report', 'date', 'ref']:
                    info['name'] = name
                    break
        
        age_patterns = [
            r'(?:age)[\s:]+?(\d{1,3})\s*(?:years|yrs|y)?',
            r'(\d{1,3})\s*(?:years|yrs|y)\s*(?:old)?',
        ]
        
        for pattern in age_patterns:
            age_match = re.search(pattern, text, re.IGNORECASE)
            if age_match:
                age = int(age_match.group(1))
                if 1 < age < 120:
                    info['age'] = age
                    break
        
        gender_match = re.search(r'(?:gender|sex)[\s:]+([MFmf]|male|female|MALE|FEMALE)', text, re.IGNORECASE)
        if gender_match:
            gender = gender_match.group(1).lower()
            info['gender'] = 'M' if gender.startswith('m') else 'F'
        
        return info
    
    def extract_doctor_notes(self, text):
        notes_patterns = [
            r'(?:notes|comments|remarks|impression)[\s:]+(.+?)(?:\n\n|\Z)',
            r'(?:diagnosis)[\s:]+(.+?)(?:\n\n|\Z)',
            r'(?:prescription|medications)[\s:]+(.+?)(?:\n\n|\Z)',
        ]
        
        notes = []
        for pattern in notes_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            notes.extend(matches)
        
        return [note.strip() for note in notes if note.strip()]
    
    def process_report(self, text):
        return {
            'patient_info': self.extract_patient_info(text),
            'lab_values': self.extract_values(text),
            'doctor_notes': self.extract_doctor_notes(text),
            'extracted_at': datetime.now().isoformat()
        }
