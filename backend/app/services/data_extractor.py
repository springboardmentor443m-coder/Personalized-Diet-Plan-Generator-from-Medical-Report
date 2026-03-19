import re
from datetime import datetime


class DataExtractor:
    def __init__(self):
        self.patterns = {}
        self.test_configs = {
            'glucose': {
                'aliases': ['glucose fasting', 'fasting glucose', 'blood sugar', 'glucose'],
                'valid_range': (40, 500),
                'unit_hints': ['mg/dl', 'mmol/l'],
                'preferred_terms': ['fasting'],
                'exclude_terms': ['estimated average glucose', 'eag'],
            },
            'cholesterol_total': {
                'aliases': ['total cholesterol', 'cholesterol total', 'cholesterol, total', 'cholesterol'],
                'valid_range': (80, 500),
                'unit_hints': ['mg/dl'],
                'exclude_terms': ['hdl', 'ldl', 'vldl', 'non-hdl', 'ratio'],
            },
            'hdl': {
                'aliases': ['hdl cholesterol', 'hdl'],
                'valid_range': (10, 150),
                'unit_hints': ['mg/dl'],
                'exclude_terms': ['non-hdl'],
            },
            'ldl': {
                'aliases': ['ldl cholesterol', 'ldl'],
                'valid_range': (20, 400),
                'unit_hints': ['mg/dl'],
                'exclude_terms': ['non-hdl'],
            },
            'triglycerides': {
                'aliases': ['total triglycerides', 'triglycerides', 'triglyceride', 'tg'],
                'valid_range': (20, 1000),
                'unit_hints': ['mg/dl'],
            },
            'hba1c': {
                'aliases': ['glycosylated haemoglobin hba1c', 'glycosylated hemoglobin hba1c', 'hba1c', 'glycated hemoglobin'],
                'valid_range': (3, 20),
                'unit_hints': ['%'],
                'preferred_terms': ['whole blood', 'ghb/hba1c'],
                'exclude_terms': ['goal of therapy', 'action suggested'],
                'line_only': True,
            },
            'bmi': {
                'aliases': ['body mass index', 'bmi'],
                'valid_range': (10, 60),
                'unit_hints': [],
            },
            'weight': {
                'aliases': ['weight', 'wt'],
                'valid_range': (20, 300),
                'unit_hints': ['kg'],
                'exclude_terms': ['weight loss'],
            },
            'height': {
                'aliases': ['height', 'ht'],
                'valid_range': (100, 230),
                'unit_hints': ['cm'],
            },
            'hemoglobin': {
                'aliases': ['hemoglobin (hb)', 'haemoglobin (hb)', 'haemoglobin', 'hemoglobin'],
                'valid_range': (4, 22),
                'unit_hints': ['g/dl'],
                'preferred_terms': ['photometry', 'spectrophotometry', 'whole blood'],
                'exclude_terms': ['hba1c', 'glycosylated', 'glycated', 'variant', 'variants', 'fetal'],
            },
            'pcv': {
                'aliases': ['packed cell volume (pcv)', 'packed cell volume', 'pcv'],
                'valid_range': (10, 70),
                'unit_hints': ['%'],
                'line_only': True,
            },
            'rbc_count': {
                'aliases': ['rbc count', 'rbc counts'],
                'valid_range': (1, 10),
                'unit_hints': ['mill/mm3', 'millions/cumm'],
                'line_only': True,
            },
            'wbc_count': {
                'aliases': ['total wbc count', 'wbc count', 'total leucocyte count', 'leucocyte count'],
                'valid_range': (1000, 30000),
                'unit_hints': ['cells/cumm', 'thou/mm3'],
                'scale_if_below': 1000,
                'line_only': True,
            },
            'mcv': {
                'aliases': ['mean corpuscular volume (mcv)', 'mean corpuscular volume', 'mcv'],
                'valid_range': (40, 130),
                'unit_hints': ['fl'],
                'line_only': True,
            },
            'mch': {
                'aliases': ['mean corpuscular hb. (mch)', 'mean corpuscular hb (mch)', 'mch'],
                'valid_range': (10, 45),
                'unit_hints': ['pg'],
                'line_only': True,
            },
            'mchc': {
                'aliases': ['mchc', 'mean corpuscular hemoglobin concentration'],
                'valid_range': (20, 45),
                'unit_hints': ['g/dl'],
                'line_only': True,
            },
            'esr': {
                'aliases': ['erythrocyte sedimentation rate (esr)', 'erythrocyte sedimentation rate', 'esr'],
                'valid_range': (0, 100),
                'unit_hints': ['mm/hr', 'mm/hr.'],
                'line_only': True,
            },
            'creatinine': {
                'aliases': ['creatinine, serum', 'creatinine serum', 'creatinine'],
                'valid_range': (0.2, 20),
                'unit_hints': ['mg/dl'],
                'exclude_terms': ['urine', '24 hrs', '24 hour', 'ratio', 'equation', 'egfr'],
                'line_only': True,
            },
            'uric_acid': {
                'aliases': ['uric acid'],
                'valid_range': (1, 20),
                'unit_hints': ['mg/dl'],
            },
            'urea': {
                'aliases': ['blood urea', 'urea'],
                'valid_range': (5, 300),
                'unit_hints': ['mg/dl'],
                'exclude_terms': ['urea nitrogen', 'bun', 'bun/creatinine'],
            },
            'vitamin_d': {
                'aliases': ['25 hydroxy vitamin d', '25-oh vitamin d', 'vitamin d'],
                'valid_range': (1, 150),
                'unit_hints': ['ng/ml'],
            },
            'vitamin_b12': {
                'aliases': ['vitamin b12', 'b12'],
                'valid_range': (50, 2000),
                'unit_hints': ['pg/ml'],
            },
            'tsh': {
                'aliases': ['thyroid stimulating hormone', 'tsh'],
                'valid_range': (0.01, 100),
                'unit_hints': ['uiu/ml', 'miu/l', 'µiu/ml'],
            },
            'platelets': {
                'aliases': ['platelet count', 'platelets'],
                'valid_range': (10, 1000000),
                'unit_hints': ['/cumm', 'cells/cumm', 'lakhs', '10ˆ3/µl', '10^3/µl', 'thou/mm3'],
                'scale_if_below': 1000,
                'line_only': True,
            },
            'sodium': {
                'aliases': ['sodium, serum', 'sodium'],
                'valid_range': (110, 170),
                'unit_hints': ['meq/l', 'mmol/l'],
            },
            'potassium': {
                'aliases': ['potassium, serum', 'potassium'],
                'valid_range': (2, 8),
                'unit_hints': ['meq/l', 'mmol/l'],
            },
            'chloride': {
                'aliases': ['chloride'],
                'valid_range': (70, 130),
                'unit_hints': ['meq/l', 'mmol/l'],
            },
        }
        self.test_metadata = {
            'glucose': {'label': 'Blood Sugar', 'unit': 'mg/dL'},
            'cholesterol_total': {'label': 'Cholesterol', 'unit': 'mg/dL'},
            'hdl': {'label': 'HDL', 'unit': 'mg/dL'},
            'ldl': {'label': 'LDL', 'unit': 'mg/dL'},
            'triglycerides': {'label': 'Triglycerides', 'unit': 'mg/dL'},
            'hba1c': {'label': 'HbA1c', 'unit': '%'},
            'bmi': {'label': 'BMI', 'unit': ''},
            'weight': {'label': 'Weight', 'unit': 'kg'},
            'height': {'label': 'Height', 'unit': 'cm'},
            'bp_systolic': {'label': 'BP Systolic', 'unit': 'mmHg'},
            'bp_diastolic': {'label': 'BP Diastolic', 'unit': 'mmHg'},
            'hemoglobin': {'label': 'Hemoglobin', 'unit': 'g/dL'},
            'pcv': {'label': 'PCV', 'unit': '%'},
            'rbc_count': {'label': 'RBC Count', 'unit': 'mill/mm3'},
            'wbc_count': {'label': 'WBC Count', 'unit': '/cumm'},
            'mcv': {'label': 'MCV', 'unit': 'fL'},
            'mch': {'label': 'MCH', 'unit': 'pg'},
            'mchc': {'label': 'MCHC', 'unit': 'g/dL'},
            'esr': {'label': 'ESR', 'unit': 'mm/hr'},
            'creatinine': {'label': 'Creatinine', 'unit': 'mg/dL'},
            'uric_acid': {'label': 'Uric Acid', 'unit': 'mg/dL'},
            'urea': {'label': 'Urea', 'unit': 'mg/dL'},
            'vitamin_d': {'label': 'Vitamin D', 'unit': 'ng/mL'},
            'vitamin_b12': {'label': 'Vitamin B12', 'unit': 'pg/mL'},
            'tsh': {'label': 'TSH', 'unit': 'uIU/mL'},
            'platelets': {'label': 'Platelets', 'unit': '/cumm'},
            'sodium': {'label': 'Sodium', 'unit': 'mmol/L'},
            'potassium': {'label': 'Potassium', 'unit': 'mmol/L'},
            'chloride': {'label': 'Chloride', 'unit': 'mmol/L'},
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
            'hemoglobin': {'low': (0, 12), 'normal': (12, 17.5), 'high': (17.5, 25)},
            'pcv': {'low': (0, 36), 'normal': (36, 50), 'high': (50, 70)},
            'rbc_count': {'low': (0, 4.0), 'normal': (4.0, 6.1), 'high': (6.1, 10)},
            'wbc_count': {'low': (0, 4000), 'normal': (4000, 11001), 'high': (11001, 30000)},
            'mcv': {'low': (0, 80), 'normal': (80, 101), 'high': (101, 130)},
            'mch': {'low': (0, 27), 'normal': (27, 33), 'high': (33, 45)},
            'mchc': {'low': (0, 31.5), 'normal': (31.5, 36.1), 'high': (36.1, 45)},
            'esr': {'normal': (0, 20), 'high': (20, 100)},
            'creatinine': {'low': (0, 0.6), 'normal': (0.6, 1.3), 'high': (1.3, 20)},
            'uric_acid': {'low': (0, 3.5), 'normal': (3.5, 7.2), 'high': (7.2, 20)},
            'urea': {'low': (0, 15), 'normal': (15, 40), 'high': (40, 300)},
            'vitamin_d': {'deficient': (0, 20), 'insufficient': (20, 30), 'normal': (30, 100), 'high': (100, 150)},
            'vitamin_b12': {'low': (0, 200), 'normal': (200, 900), 'high': (900, 2000)},
            'tsh': {'low': (0, 0.4), 'normal': (0.4, 4.5), 'high': (4.5, 100)},
            'platelets': {'low': (0, 150000), 'normal': (150000, 450000), 'high': (450000, 1000000)},
            'sodium': {'low': (0, 135), 'normal': (135, 146), 'high': (146, 170)},
            'potassium': {'low': (0, 3.5), 'normal': (3.5, 5.2), 'high': (5.2, 8)},
            'chloride': {'low': (0, 98), 'normal': (98, 108), 'high': (108, 130)},
        }

    def extract_values(self, text):
        text_lower = text.lower()
        results = {}

        bp_match = re.search(r'\b(?:bp|blood pressure|b\.p\.)\b[^\n\r\d]{0,20}(\d{2,3})\s*/\s*(\d{2,3})', text_lower, re.IGNORECASE)
        if bp_match:
            systolic = float(bp_match.group(1))
            diastolic = float(bp_match.group(2))
            results['bp_systolic'] = self._build_result('bp_systolic', systolic)
            results['bp_diastolic'] = self._build_result('bp_diastolic', diastolic)

        lines = [line.strip() for line in text_lower.splitlines() if line.strip()]
        for key, config in self.test_configs.items():
            candidate = self._extract_metric(text_lower, lines, config)
            if candidate is None:
                continue
            results[key] = self._build_result(key, candidate)

        return results

    def _build_result(self, key, value):
        metadata = self.test_metadata.get(key, {})
        normalized_value = round(value, 2) if isinstance(value, float) and not value.is_integer() else int(value) if isinstance(value, float) else value
        return {
            'value': normalized_value,
            'status': self._check_threshold(key, value),
            'label': metadata.get('label', key.replace('_', ' ').title()),
            'unit': metadata.get('unit', ''),
        }

    def _extract_metric(self, text, lines, config):
        best_score = float('-inf')
        best_value = None
        alias_pattern = self._build_alias_pattern(config['aliases'])

        seen_contexts = set()
        contexts = []
        for index, line in enumerate(lines):
            compact_line = line.strip().lower()
            if not compact_line:
                continue
            contexts.append(compact_line)

            if re.search(alias_pattern, compact_line) and not re.search(r'(?<![/\d])(\d+(?:\.\d+)?)', compact_line) and index < len(lines) - 1:
                contexts.append(f"{compact_line} {lines[index + 1].strip().lower()}")

        if not config.get('line_only'):
            contexts.extend(self._build_text_windows(text, alias_pattern))

        for compact_line in contexts:
            if compact_line in seen_contexts:
                continue
            seen_contexts.add(compact_line)

            if any(marker in compact_line for marker in self.noise_markers):
                continue
            if any(term in compact_line for term in config.get('exclude_terms', [])):
                continue

            alias_match = re.search(alias_pattern, compact_line)
            if not alias_match:
                continue

            alias_text = alias_match.group(0)
            alias_pos = alias_match.start()
            for value, raw_token, token_start in self._extract_numeric_candidates(compact_line, config):
                score = self._score_candidate(compact_line, alias_text, alias_pos, token_start, raw_token, value, config)
                if score > best_score:
                    best_score = score
                    best_value = value

        return best_value


    def _build_line_contexts(self, lines):
        return list(lines)

    def _build_alias_pattern(self, aliases):
        sorted_aliases = sorted(aliases, key=len, reverse=True)
        return r'(?<![a-z])(' + '|'.join(re.escape(alias) for alias in sorted_aliases) + r')(?![a-z])'

    def _build_text_windows(self, text, alias_pattern):
        windows = []
        for match in re.finditer(alias_pattern, text):
            start = max(0, match.start() - 24)
            end = min(len(text), match.end() + 72)
            windows.append(text[start:end].replace('\n', ' '))
        return windows

    def _extract_numeric_candidates(self, line, config):
        candidates = []
        for num_match in re.finditer(r'(?<![/\d])(\d+(?:\.\d+)?)', line):
            raw_token = num_match.group(1)
            for value in self._expand_numeric_candidates(raw_token, config['valid_range']):
                if config.get('scale_if_below') and value < config['scale_if_below']:
                    value *= config['scale_if_below']
                candidates.append((value, raw_token, num_match.start()))
        return candidates

    def _expand_numeric_candidates(self, raw_token, valid_range):
        min_val, max_val = valid_range
        valid_values = []
        seen = set()

        for start in range(len(raw_token)):
            candidate = raw_token[start:]
            if candidate.count('.') > 1:
                continue
            try:
                value = float(candidate)
            except ValueError:
                continue

            rounded = round(value, 4)
            if rounded in seen:
                continue
            if min_val <= value <= max_val:
                valid_values.append(value)
                seen.add(rounded)

        return valid_values

    def _score_candidate(self, line, alias_text, alias_pos, token_start, raw_token, value, config):
        score = 0
        distance = abs(token_start - alias_pos)
        score += max(0, 170 - distance * 3)

        before_gap = alias_pos - (token_start + len(raw_token))
        after_gap = token_start - (alias_pos + len(alias_text))
        if 0 <= before_gap <= 12:
            score += 60
        if 0 <= after_gap <= 12:
            score += 55

        unit_found = any(unit in line for unit in config['unit_hints'])
        if unit_found:
            score += 18
        elif config['unit_hints']:
            score -= 20
        if any(term in line for term in config.get('preferred_terms', [])):
            score += 24

        if re.search(rf'{re.escape(raw_token)}\s*-\s*\d', line):
            score -= 45
        if re.search(rf'\d\s*-\s*{re.escape(raw_token)}', line):
            score -= 45
        if re.search(rf'[<>]\s*{re.escape(raw_token)}', line):
            score -= 45

        context_start = max(0, token_start - 24)
        context_end = min(len(line), token_start + len(raw_token) + 24)
        candidate_context = line[context_start:context_end]
        penalty_terms = ['high', 'low', 'risk', 'desirable', 'borderline', 'normal', 'optimal', 'reference', 'calculated']
        if any(term in candidate_context for term in penalty_terms):
            score -= 20
        if any(term in line for term in ['goal of therapy', 'action suggested', 'interpretation notes']):
            score -= 35
        if 'page ' in line:
            score -= 150

        numeric_matches = list(re.finditer(r'(?<![/\d])(\d+(?:\.\d+)?)', line))
        if numeric_matches and numeric_matches[-1].start() == token_start:
            score += 35

        if alias_text in ['hemoglobin', 'haemoglobin'] and 'hba1c' in line:
            score -= 80
        if alias_text in ['hemoglobin', 'haemoglobin']:
            if 'g/dl' in candidate_context:
                score += 20
            else:
                score -= 40
        if alias_text == 'hba1c':
            if '%' in candidate_context:
                score += 20
            else:
                score -= 35
        if alias_text == 'cholesterol' and any(term in line for term in ['hdl', 'ldl', 'vldl', 'non-hdl']):
            score -= 80
        if alias_text == 'urea' and any(term in line for term in ['urea nitrogen', 'bun']):
            score -= 80
        score += len(alias_text)


        return score

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
