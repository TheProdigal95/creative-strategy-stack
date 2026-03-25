#!/usr/bin/env python3
"""
Evidence Matcher - Step 08 of Research Engine

Counts evidence matches for each insight using pattern matching.

Usage:
    python3 engine/step08_evidence_matcher.py pureplank 01_weight-loss-men-dads
    python3 engine/step08_evidence_matcher.py pureplank 01_weight-loss-men-dads --verbose
"""

import os
import sys
import json
import pandas as pd
import argparse
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

def load_themes(json_path):
    """Load themes_discovered.json from sprint folder."""
    with open(json_path, 'r') as f:
        return json.load(f)

def load_evidence(csv_path):
    """Load evidence_filtered.csv into pandas dataframe."""
    print(f"Loading evidence from: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"  Total evidence pieces: {len(df):,}")
    return df

def matches_pattern(text, pattern):
    """Check if pattern matches in text using word boundary matching."""
    if pd.isna(text):
        return False

    # Case insensitive, word boundary matching
    pattern_escaped = re.escape(pattern.lower())
    regex = r'\b' + pattern_escaped + r'\b'

    return bool(re.search(regex, text.lower()))

def find_matching_evidence(insight_patterns, evidence_df, verbose=False):
    """Find all evidence that matches any pattern for this insight."""

    matched_indices = set()
    pattern_match_counts = Counter()

    # For each pattern, find matching evidence
    for pattern in insight_patterns:
        matches_for_pattern = evidence_df['text'].apply(
            lambda text: matches_pattern(text, pattern)
        )

        pattern_matches = evidence_df[matches_for_pattern].index.tolist()
        matched_indices.update(pattern_matches)
        pattern_match_counts[pattern] = len(pattern_matches)

    # Get matched evidence dataframe
    matched_evidence = evidence_df.loc[list(matched_indices)]

    return matched_evidence, pattern_match_counts

def aggregate_sources(matched_evidence):
    """Get unique sources from matched evidence."""
    if len(matched_evidence) == 0:
        return []

    sources = matched_evidence['source'].dropna().unique().tolist()
    return sorted(sources)

def get_top_communities(matched_evidence, top_n=3):
    """Get top N communities by match frequency."""
    if len(matched_evidence) == 0:
        return []

    community_counts = matched_evidence['community'].value_counts()
    top_communities = community_counts.head(top_n).index.tolist()

    return top_communities

def select_best_quotes(matched_evidence, num_quotes=5):
    """Select best quotes based on relevance_score."""
    if len(matched_evidence) == 0:
        return []

    # Sort by relevance_score (descending) and take top N
    sorted_evidence = matched_evidence.sort_values('relevance_score', ascending=False)
    top_evidence = sorted_evidence.head(num_quotes)

    best_quotes = []
    for _, row in top_evidence.iterrows():
        # Truncate text to 300 characters for readability
        text = str(row['text']) if pd.notna(row['text']) else ""
        if len(text) > 300:
            text = text[:300] + "..."

        quote = {
            'text': text,
            'evidence_id': row['evidence_id'],
            'community': row['community'] if pd.notna(row['community']) else None,
            'relevance_score': int(row['relevance_score']) if pd.notna(row['relevance_score']) else 0
        }
        best_quotes.append(quote)

    return best_quotes

def process_insight(insight, evidence_df, verbose=False):
    """Process one insight: match evidence and aggregate stats."""

    patterns = insight.get('matching_patterns', [])

    if not patterns:
        return {
            'evidence_count': 0,
            'sources': [],
            'top_communities': [],
            'best_quotes': [],
            'matched_evidence_ids': []
        }

    # Find matching evidence
    matched_evidence, pattern_counts = find_matching_evidence(patterns, evidence_df, verbose)

    # Aggregate stats
    evidence_count = len(matched_evidence)
    sources = aggregate_sources(matched_evidence)
    top_communities = get_top_communities(matched_evidence, top_n=3)
    best_quotes = select_best_quotes(matched_evidence, num_quotes=5)

    # Persist matched evidence IDs so Step 10 can skip regex re-matching
    matched_evidence_ids = matched_evidence['evidence_id'].tolist()

    return {
        'evidence_count': evidence_count,
        'sources': sources,
        'top_communities': top_communities,
        'best_quotes': best_quotes,
        'matched_evidence_ids': matched_evidence_ids,
        'pattern_match_counts': dict(pattern_counts)  # For reporting
    }

def update_themes_with_evidence(themes_data, evidence_df, verbose=False):
    """Update all insights with evidence matching results."""

    print("\nMatching evidence to insights...")

    total_insights = 0
    insights_with_evidence = 0

    for theme_idx, theme in enumerate(themes_data.get('themes', [])):
        theme_name = theme.get('theme_name', 'Unknown')

        for insight_idx, insight in enumerate(theme.get('insights', [])):
            total_insights += 1

            if verbose:
                print(f"  Processing: {theme_name} / {insight.get('angle', 'Unknown')}")

            # Process this insight
            results = process_insight(insight, evidence_df, verbose)

            # Add results to insight
            insight['evidence_count'] = results['evidence_count']
            insight['sources'] = results['sources']
            insight['top_communities'] = results['top_communities']
            insight['best_quotes'] = results['best_quotes']
            insight['matched_evidence_ids'] = results.get('matched_evidence_ids', [])

            # Store pattern counts for reporting (not in final output)
            insight['_pattern_match_counts'] = results['pattern_match_counts']

            if results['evidence_count'] > 0:
                insights_with_evidence += 1

    print(f"  Processed {total_insights} insights")
    print(f"  {insights_with_evidence} insights have matching evidence ({insights_with_evidence/total_insights*100:.1f}%)")

    return themes_data

def save_themes(themes_data, output_path):
    """Save updated themes with evidence counts."""

    # Remove temporary pattern counts before saving
    for theme in themes_data.get('themes', []):
        for insight in theme.get('insights', []):
            if '_pattern_match_counts' in insight:
                del insight['_pattern_match_counts']

    with open(output_path, 'w') as f:
        json.dump(themes_data, f, indent=2)

    print(f"✓ Updated themes with evidence counts: {output_path}")

def generate_evidence_report(themes_data, output_path):
    """Generate detailed evidence matching report."""

    report = f"""EVIDENCE MATCHING REPORT
{'='*80}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY STATISTICS:
{'-'*80}
"""

    total_insights = 0
    total_evidence_matched = 0
    insights_with_evidence = 0

    for theme in themes_data.get('themes', []):
        for insight in theme.get('insights', []):
            total_insights += 1
            count = insight.get('evidence_count', 0)
            total_evidence_matched += count
            if count > 0:
                insights_with_evidence += 1

    avg_evidence_per_insight = total_evidence_matched / max(total_insights, 1)

    report += f"Total insights: {total_insights}\n"
    report += f"Insights with evidence: {insights_with_evidence} ({insights_with_evidence/total_insights*100:.1f}%)\n"
    report += f"Insights without evidence: {total_insights - insights_with_evidence}\n"
    report += f"Total evidence matches: {total_evidence_matched:,}\n"
    report += f"Average evidence per insight: {avg_evidence_per_insight:.1f}\n"

    # Detailed per-insight stats
    report += f"\n\nDETAILED RESULTS BY INSIGHT:\n{'='*80}\n"

    for theme in themes_data.get('themes', []):
        theme_name = theme.get('theme_name', 'Unknown')

        for insight in theme.get('insights', []):
            angle = insight.get('angle', 'Unknown')
            evidence_count = insight.get('evidence_count', 0)
            sources = insight.get('sources', [])
            communities = insight.get('top_communities', [])
            patterns = insight.get('matching_patterns', [])

            report += f"\n{theme_name} / {angle}\n"
            report += f"{'-'*80}\n"
            report += f"Evidence Count: {evidence_count}\n"
            report += f"Sources: {', '.join(sources) if sources else 'None'}\n"
            report += f"Top Communities: {', '.join(communities) if communities else 'None'}\n"
            report += f"Patterns ({len(patterns)}): {', '.join(patterns[:5])}{'...' if len(patterns) > 5 else ''}\n"

            # Show pattern match breakdown if available
            pattern_counts = insight.get('_pattern_match_counts', {})
            if pattern_counts:
                top_patterns = sorted(pattern_counts.items(), key=lambda x: -x[1])[:5]
                report += f"Top Matching Patterns:\n"
                for pattern, count in top_patterns:
                    report += f"  - \"{pattern}\": {count} matches\n"

    report += "\n" + "="*80 + "\n"

    with open(output_path, 'w') as f:
        f.write(report)

    print(f"✓ Generated evidence report: {output_path}")

def print_summary(themes_data):
    """Print summary statistics."""

    print("\n" + "="*80)
    print("EVIDENCE MATCHING SUMMARY")
    print("="*80)

    total_insights = 0
    evidence_counts = []
    zero_evidence = 0

    for theme in themes_data.get('themes', []):
        for insight in theme.get('insights', []):
            total_insights += 1
            count = insight.get('evidence_count', 0)
            evidence_counts.append(count)
            if count == 0:
                zero_evidence += 1

    if evidence_counts:
        avg_count = sum(evidence_counts) / len(evidence_counts)
        max_count = max(evidence_counts)
        min_count = min(evidence_counts)

        print(f"\nTotal insights: {total_insights}")
        print(f"Insights with evidence: {total_insights - zero_evidence} ({(total_insights - zero_evidence)/total_insights*100:.1f}%)")
        print(f"Insights without evidence: {zero_evidence}")
        print(f"\nEvidence counts:")
        print(f"  Average: {avg_count:.1f}")
        print(f"  Min: {min_count}")
        print(f"  Max: {max_count}")

        # Show top 5 insights by evidence count
        insights_with_counts = []
        for theme in themes_data.get('themes', []):
            for insight in theme.get('insights', []):
                insights_with_counts.append({
                    'theme': theme.get('theme_name', 'Unknown'),
                    'angle': insight.get('angle', 'Unknown'),
                    'count': insight.get('evidence_count', 0)
                })

        top_insights = sorted(insights_with_counts, key=lambda x: -x['count'])[:5]

        print(f"\nTop 5 insights by evidence count:")
        for i, item in enumerate(top_insights, 1):
            print(f"  {i}. {item['theme']} / {item['angle']}: {item['count']} matches")

    print("\n" + "="*80)

def main():
    parser = argparse.ArgumentParser(description='Match evidence to insights using pattern matching')
    parser.add_argument('brand', help='Brand name (e.g., pureplank)')
    parser.add_argument('sprint', help='Sprint folder name (e.g., 01_weight-loss-men-dads)')
    parser.add_argument('--verbose', action='store_true',
                       help='Print detailed progress')

    args = parser.parse_args()

    # Paths
    intermediate_dir = f"brands/{args.brand}/sprints/{args.sprint}/_intermediate"
    themes_path = f"{intermediate_dir}/themes_discovered.json"
    evidence_path = f"{intermediate_dir}/evidence_filtered.csv"
    report_path = f"{intermediate_dir}/evidence_matching_report.txt"

    print("="*80)
    print("EVIDENCE MATCHER - PHASE 1B")
    print("="*80)
    print(f"Brand: {args.brand}")
    print(f"Sprint: {args.sprint}")
    print()

    # Load inputs
    print("Loading data...")
    themes_data = load_themes(themes_path)
    evidence_df = load_evidence(evidence_path)

    # Process all insights
    updated_themes = update_themes_with_evidence(themes_data, evidence_df, verbose=args.verbose)

    # Save outputs
    print("\nSaving results...")
    save_themes(updated_themes, themes_path)
    generate_evidence_report(updated_themes, report_path)

    # Print summary
    print_summary(updated_themes)

    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)

if __name__ == '__main__':
    main()
