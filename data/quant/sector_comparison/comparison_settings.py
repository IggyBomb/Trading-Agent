"""

Usage:
    from comparison_settings import MIN_PEERS_FOR_MEDIAN, MIN_NAMES_FOR_REGION, GRADES, GRADE_BANDS
"""

# ── Peer group ──
# Use the ticker's own region (US / Europe) only if its sector has at least this many
# names there (with or without data); otherwise compare against the sector in all regions.
# README D6
MIN_NAMES_FOR_REGION = 10

# Name of the peer group used when the region is too small
ALL_REGIONS = "All regions"

# ── Median ──
# A sector median is only shown if at least this many peers have a value
# (the ticker itself counts). README D5
# (No sector mean: the workbook's trimmed mean is display-only and never affects a grade.)
MIN_PEERS_FOR_MEDIAN = 3

# ── Grades ──
# From worst to best. README G6:G18
GRADES = ["F", "D-", "D", "D+", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"]

# Lowest percentile (0-1) for each grade above, same order: today 13 equal bands
# (0, 1/13, 2/13, ...). To change the cut-offs, edit this list. README F6:F18
GRADE_BANDS = [i / len(GRADES) for i in range(len(GRADES))]

# Grade shown when a metric has no percentile (no value), and when a pillar has no scored metric
NO_GRADE_METRIC = "NM"
NO_GRADE_PILLAR = "-"
