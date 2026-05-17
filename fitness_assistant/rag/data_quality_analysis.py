"""
Data Quality Analysis Script for Fitness Assistant RAG Project
Analyzes the detailed_exercise_dataset.csv file focusing on instruction quality
"""

import pandas as pd
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple


class InstructionQualityAnalyzer:
    """Analyzes instruction quality in exercise datasets"""
    
    # Quality scoring criteria
    MIN_INSTRUCTION_LENGTH = 30
    MAX_INSTRUCTION_LENGTH = 500
    QUALITY_THRESHOLD = 5.0
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        self.quality_scores = []
        self.flagged_entries = []
        
    def score_instruction(self, instruction: str, index: int) -> Dict:
        """Score an instruction on a 1-10 scale based on quality criteria"""
        score = 10.0
        issues = []
        
        # Check for missing/null values
        if pd.isna(instruction) or instruction == "":
            return {
                "index": index,
                "exercise_name": self.df.iloc[index].get("Exercise Name", "Unknown"),
                "instruction": "",
                "score": 1.0,
                "issues": ["Missing instruction"],
                "length": 0
            }
        
        instruction_str = str(instruction).strip()
        instruction_length = len(instruction_str)
        
        # Check length
        if instruction_length < self.MIN_INSTRUCTION_LENGTH:
            score -= 3.0
            issues.append(f"Too short ({instruction_length} chars, min {self.MIN_INSTRUCTION_LENGTH})")
        
        if instruction_length > self.MAX_INSTRUCTION_LENGTH:
            score -= 1.0
            issues.append(f"Potentially too long ({instruction_length} chars)")
        
        # Check for vagueness - generic terms that indicate poor quality
        vague_terms = [
            "do the exercise", "perform the movement", "move your body",
            "keep moving", "repeat", "continue", "until done"
        ]
        vague_count = sum(1 for term in vague_terms if term.lower() in instruction_str.lower())
        if vague_count > 0:
            score -= vague_count * 1.5
            issues.append(f"Contains {vague_count} vague terms")
        
        # Check for lack of specificity
        if not any(word in instruction_str.lower() for word in ["position", "angle", "straight", "bend", "extend", "contract", "engage", "shoulder", "width", "height", "distance", "grip", "hold", "count", "tempo", "breathing"]):
            score -= 2.0
            issues.append("Lacks specific technical details")
        
        # Check for common instruction patterns
        has_starting_position = any(word in instruction_str.lower() for word in ["start", "begin", "lie", "stand", "sit"])
        has_movement_description = any(word in instruction_str.lower() for word in ["lower", "raise", "lift", "push", "pull", "rotate", "twist", "flex", "straighten"])
        has_ending_position = any(word in instruction_str.lower() for word in ["return", "back to", "complete", "finish"])
        
        if not has_starting_position and not has_movement_description:
            score -= 2.0
            issues.append("Missing movement description")
        
        # Check for common copy-paste issues (same instruction repeated)
        instruction_word_count = len(instruction_str.split())
        if instruction_word_count < 10:
            score -= 1.5
            issues.append("Very brief instruction (potentially incomplete)")
        
        # Ensure score is between 1 and 10
        score = max(1.0, min(10.0, score))
        
        return {
            "index": index,
            "exercise_name": self.df.iloc[index].get("Exercise Name", "Unknown"),
            "instruction": instruction_str[:100] + "..." if len(instruction_str) > 100 else instruction_str,
            "full_instruction": instruction_str,
            "score": round(score, 2),
            "issues": issues,
            "length": instruction_length,
            "has_starting_position": has_starting_position,
            "has_movement_description": has_movement_description,
            "has_ending_position": has_ending_position
        }
    
    def analyze(self) -> Dict:
        """Run the complete analysis"""
        print("Starting data quality analysis...")
        
        # Check if Instructions column exists
        if "Instructions" not in self.df.columns:
            raise ValueError(f"'Instructions' column not found. Available columns: {self.df.columns.tolist()}")
        
        total_entries = len(self.df)
        print(f"Total entries to analyze: {total_entries}")
        
        # Score all instructions
        for idx, instruction in enumerate(self.df["Instructions"]):
            score_result = self.score_instruction(instruction, idx)
            self.quality_scores.append(score_result)
            
            if score_result["score"] < self.QUALITY_THRESHOLD:
                self.flagged_entries.append(score_result)
        
        # Calculate statistics
        scores = [item["score"] for item in self.quality_scores]
        flagged_count = len(self.flagged_entries)
        
        # Sort flagged entries by score
        self.flagged_entries.sort(key=lambda x: x["score"])
        
        statistics = {
            "total_entries": total_entries,
            "missing_instructions": sum(1 for item in self.quality_scores if item["issues"] and "Missing instruction" in item["issues"]),
            "flagged_entries_count": flagged_count,
            "flagged_percentage": round((flagged_count / total_entries) * 100, 2),
            "avg_score": round(sum(scores) / len(scores), 2),
            "median_score": round(sorted(scores)[len(scores) // 2], 2),
            "min_score": min(scores),
            "max_score": max(scores),
            "quality_threshold": self.QUALITY_THRESHOLD,
            "score_distribution": {
                "excellent_9_10": len([s for s in scores if s >= 9]),
                "good_7_8": len([s for s in scores if 7 <= s < 9]),
                "fair_5_6": len([s for s in scores if 5 <= s < 7]),
                "poor_1_4": len([s for s in scores if s < 5])
            }
        }
        
        return {
            "analysis_metadata": {
                "dataset_path": self.csv_path,
                "total_columns": len(self.df.columns),
                "columns": self.df.columns.tolist()
            },
            "statistics": statistics,
            "worst_entries": self.flagged_entries[:10],
            "all_quality_scores": self.quality_scores
        }


def main():
    """Main execution function"""
    script_dir = Path(__file__).parent
    csv_path = script_dir / "data" / "detailed_exercise_dataset.csv"
    output_path = script_dir / "data_quality_report.json"
    
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        return
    
    # Run analysis
    analyzer = InstructionQualityAnalyzer(str(csv_path))
    results = analyzer.analyze()
    
    # Save report
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nData Quality Report Summary")
    print("=" * 50)
    stats = results["statistics"]
    print(f"Total Entries: {stats['total_entries']}")
    print(f"Missing Instructions: {stats['missing_instructions']}")
    print(f"Flagged (score < {stats['quality_threshold']}): {stats['flagged_entries_count']} ({stats['flagged_percentage']}%)")
    print(f"Average Score: {stats['avg_score']}/10")
    print(f"Median Score: {stats['median_score']}/10")
    print(f"\nScore Distribution:")
    print(f"  Excellent (9-10): {stats['score_distribution']['excellent_9_10']}")
    print(f"  Good (7-8): {stats['score_distribution']['good_7_8']}")
    print(f"  Fair (5-6): {stats['score_distribution']['fair_5_6']}")
    print(f"  Poor (1-4): {stats['score_distribution']['poor_1_4']}")
    
    print(f"\nReport saved to: {output_path}")
    
    # Print top 5 worst entries
    if results["worst_entries"]:
        print("\nTop 5 Worst Quality Entries:")
        print("-" * 50)
        for i, entry in enumerate(results["worst_entries"][:5], 1):
            print(f"{i}. {entry['exercise_name']} (Score: {entry['score']})")
            print(f"   Issues: {', '.join(entry['issues'])}")
            print(f"   Instruction: {entry['instruction'][:80]}...")


if __name__ == "__main__":
    main()
