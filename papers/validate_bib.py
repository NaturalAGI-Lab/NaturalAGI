#!/usr/bin/env python3

import sys
import os
import shutil
import json
import time
from typing import Dict, List, Tuple, Set
from difflib import SequenceMatcher
import requests

try:
    import bibtexparser
    from bibtexparser.bwriter import BibTexWriter
    from bibtexparser.bibdatabase import BibDatabase
except ImportError:
    print("Error: bibtexparser not found. Install with: pip install bibtexparser")
    sys.exit(1)


REQUIRED_FIELDS = {
    'article': ['author', 'title', 'journal', 'year'],
    'inproceedings': ['author', 'title', 'booktitle', 'year'],
    'book': ['author', 'title', 'publisher', 'year'],
    'incollection': ['author', 'title', 'booktitle', 'publisher', 'year'],
    'phdthesis': ['author', 'title', 'school', 'year'],
    'mastersthesis': ['author', 'title', 'school', 'year'],
    'techreport': ['author', 'title', 'institution', 'year'],
    'misc': ['year'],
}

STANDARD_FIELD_NAMES = {
    'author', 'title', 'journal', 'booktitle', 'year', 'volume', 'number',
    'pages', 'publisher', 'editor', 'organization', 'school', 'institution',
    'doi', 'url', 'isbn', 'issn', 'month', 'note', 'key', 'address',
    'edition', 'series', 'chapter', 'howpublished', 'eprint', 'archiveprefix',
    'primaryclass', 'keywords'
}


class BibTexValidator:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.issues = []
        self.warnings = []
        self.fixes_applied = []
        self.database = None
        
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        if not os.path.exists(self.filepath):
            self.issues.append(f"File not found: {self.filepath}")
            return False, self.issues, self.warnings
            
        try:
            with open(self.filepath, 'r', encoding='utf-8') as bibfile:
                self.database = bibtexparser.load(bibfile)
        except Exception as e:
            self.issues.append(f"Failed to parse BibTeX file: {str(e)}")
            return False, self.issues, self.warnings
        
        print(f"\n{'='*70}")
        print(f"Validating: {self.filepath}")
        print(f"Total entries: {len(self.database.entries)}")
        print(f"{'='*70}\n")
        
        self._check_required_fields()
        self._check_duplicates()
        self._check_field_names()
        self._validate_external_references()
        
        has_errors = len(self.issues) > 0
        return not has_errors, self.issues, self.warnings
    
    def _check_required_fields(self):
        print("Checking required fields...")
        missing_fields_count = 0
        
        for entry in self.database.entries:
            entry_type = entry.get('ENTRYTYPE', '').lower()
            entry_id = entry.get('ID', 'unknown')
            
            if entry_type in REQUIRED_FIELDS:
                required = REQUIRED_FIELDS[entry_type]
                missing = []
                
                for field in required:
                    if field not in entry or not entry[field].strip():
                        missing.append(field)
                
                if missing:
                    missing_fields_count += 1
                    self.issues.append(
                        f"Entry '{entry_id}' (@{entry_type}): missing required fields: {', '.join(missing)}"
                    )
        
        if missing_fields_count == 0:
            print("✓ All entries have required fields\n")
        else:
            print(f"✗ Found {missing_fields_count} entries with missing fields\n")
    
    def _check_duplicates(self):
        print("Checking for duplicates...")
        
        seen_ids = {}
        seen_dois = {}
        titles = []
        
        duplicate_ids = 0
        duplicate_dois = 0
        duplicate_titles = 0
        
        for idx, entry in enumerate(self.database.entries):
            entry_id = entry.get('ID', '')
            
            if entry_id in seen_ids:
                duplicate_ids += 1
                self.issues.append(
                    f"Duplicate citation key: '{entry_id}' (entries {seen_ids[entry_id]} and {idx})"
                )
            else:
                seen_ids[entry_id] = idx
            
            if 'doi' in entry and entry['doi'].strip():
                doi = entry['doi'].strip().lower()
                if doi in seen_dois:
                    duplicate_dois += 1
                    self.warnings.append(
                        f"Duplicate DOI: {doi} in entries '{seen_dois[doi]}' and '{entry_id}'"
                    )
                else:
                    seen_dois[doi] = entry_id
            
            if 'title' in entry and entry['title'].strip():
                title = entry['title'].strip().lower()
                titles.append((title, entry_id, idx))
        
        for i, (title1, id1, idx1) in enumerate(titles):
            for title2, id2, idx2 in titles[i+1:]:
                similarity = SequenceMatcher(None, title1, title2).ratio()
                if similarity > 0.90:
                    duplicate_titles += 1
                    self.warnings.append(
                        f"Similar titles ({similarity:.1%}): '{id1}' and '{id2}'"
                    )
        
        total_duplicates = duplicate_ids + duplicate_dois + duplicate_titles
        if total_duplicates == 0:
            print("✓ No duplicates found\n")
        else:
            print(f"✗ Found {total_duplicates} potential duplicates\n")
    
    def _check_field_names(self):
        print("Checking field names...")
        invalid_fields = set()
        
        for entry in self.database.entries:
            entry_id = entry.get('ID', 'unknown')
            for field in entry.keys():
                if field not in ['ID', 'ENTRYTYPE'] and field.lower() not in STANDARD_FIELD_NAMES:
                    invalid_fields.add(field)
                    self.warnings.append(
                        f"Entry '{entry_id}': non-standard field name '{field}'"
                    )
        
        if len(invalid_fields) == 0:
            print("✓ All field names are standard\n")
        else:
            print(f"⚠ Found {len(invalid_fields)} non-standard field names\n")
    
    def _validate_external_references(self):
        print("Validating external references (DOI and arXiv)...")
        doi_count = 0
        arxiv_count = 0
        doi_valid = 0
        arxiv_valid = 0
        
        for entry in self.database.entries:
            entry_id = entry.get('ID', 'unknown')
            
            if 'doi' in entry and entry['doi'].strip():
                doi_count += 1
                doi = entry['doi'].strip()
                if self._validate_doi(doi):
                    doi_valid += 1
                else:
                    self.warnings.append(
                        f"Entry '{entry_id}': Could not verify DOI: {doi}"
                    )
            
            if 'eprint' in entry and entry.get('archiveprefix', '').lower() == 'arxiv':
                arxiv_count += 1
                arxiv_id = entry['eprint'].strip()
                if self._validate_arxiv(arxiv_id):
                    arxiv_valid += 1
                else:
                    self.warnings.append(
                        f"Entry '{entry_id}': Could not verify arXiv ID: {arxiv_id}"
                    )
        
        if doi_count > 0:
            print(f"  DOI: {doi_valid}/{doi_count} verified")
        if arxiv_count > 0:
            print(f"  arXiv: {arxiv_valid}/{arxiv_count} verified")
        if doi_count == 0 and arxiv_count == 0:
            print("  No DOI or arXiv references to validate")
        print()
    
    def _validate_doi(self, doi: str) -> bool:
        doi = doi.replace('https://doi.org/', '').replace('http://doi.org/', '')
        url = f"https://api.crossref.org/works/{doi}"
        
        try:
            time.sleep(1)
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def _validate_arxiv(self, arxiv_id: str) -> bool:
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        
        try:
            time.sleep(1)
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return '<entry>' in response.text
            return False
        except Exception:
            return False
    
    def auto_fix(self) -> bool:
        if not self.database:
            return False
        
        backup_path = f"{self.filepath}.bak"
        shutil.copy2(self.filepath, backup_path)
        print(f"Backup created: {backup_path}\n")
        
        print("Applying automatic fixes...")
        
        self._fix_field_names()
        self._remove_duplicate_ids()
        self._normalize_formatting()
        
        if self.fixes_applied:
            writer = BibTexWriter()
            writer.indent = '  '
            writer.order_entries_by = 'ID'
            
            with open(self.filepath, 'w', encoding='utf-8') as bibfile:
                bibfile.write(writer.write(self.database))
            
            print(f"\n✓ Applied {len(self.fixes_applied)} fixes")
            for fix in self.fixes_applied:
                print(f"  - {fix}")
            print(f"\nFixed file saved: {self.filepath}")
            return True
        else:
            print("✓ No fixes needed")
            os.remove(backup_path)
            return False
    
    def _fix_field_names(self):
        for entry in self.database.entries:
            keys_to_rename = {}
            for field in list(entry.keys()):
                if field not in ['ID', 'ENTRYTYPE']:
                    normalized = field.lower()
                    if normalized in STANDARD_FIELD_NAMES and field != normalized:
                        keys_to_rename[field] = normalized
            
            for old_key, new_key in keys_to_rename.items():
                entry[new_key] = entry.pop(old_key)
                self.fixes_applied.append(f"Normalized field '{old_key}' to '{new_key}'")
    
    def _remove_duplicate_ids(self):
        seen_ids = set()
        entries_to_keep = []
        
        for entry in self.database.entries:
            entry_id = entry.get('ID', '')
            if entry_id not in seen_ids:
                seen_ids.add(entry_id)
                entries_to_keep.append(entry)
            else:
                self.fixes_applied.append(f"Removed duplicate entry: '{entry_id}'")
        
        self.database.entries = entries_to_keep
    
    def _normalize_formatting(self):
        for entry in self.database.entries:
            for field in entry:
                if field not in ['ID', 'ENTRYTYPE']:
                    value = entry[field]
                    normalized = ' '.join(value.split())
                    if normalized != value:
                        entry[field] = normalized


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_bib.py <path-to-bib-file>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    validator = BibTexValidator(filepath)
    success, issues, warnings = validator.validate()
    
    print(f"\n{'='*70}")
    print("VALIDATION SUMMARY")
    print(f"{'='*70}")
    
    if issues:
        print(f"\n❌ ERRORS ({len(issues)}):")
        for issue in issues:
            print(f"  • {issue}")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"  • {warning}")
    
    if not issues and not warnings:
        print("\n✅ All checks passed! BibTeX file is valid.")
    
    print(f"\n{'='*70}\n")
    
    if issues or warnings:
        print("Attempting to auto-fix issues...")
        validator.auto_fix()
        print()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

