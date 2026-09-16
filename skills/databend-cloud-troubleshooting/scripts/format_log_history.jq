# Formatter for a human-readable log_history export.
#
# Input is the output of: python3 scripts/query.py --format json "<SELECT ...>"
# for this exact column order:
#   timestamp, path, target, log_level, cluster_id, node_id,
#   warehouse_id, query_id, message, fields, batch_number
#
# The first line is the column schema (an array of objects); every later line is
# one row. No row is ever dropped: an event without a timestamp still prints,
# with "-" in the timestamp column.
select(type == "array" and (.[0] | type) != "object") |
. as $row |
(try (($row[0][0:19] + "Z" | strptime("%Y-%m-%d %H:%M:%SZ") | mktime) + 28800
  | strftime("%Y-%m-%d %H:%M:%S")) catch null) as $local_seconds |
(if $local_seconds == null then "-" else $local_seconds + ($row[0][19:23] // "") end) as $local_time |
($row[3] // "INFO") as $level |
(($row[7] // "-") | tostring) as $query_id |
(($row[8] // "") | tostring
  | gsub("\r"; "\\r")
  | gsub("\n"; "\\n")
  | gsub("\t"; "\\t")) as $message |
(($row[9] // "-") | tostring
  | gsub("\r"; "\\r")
  | gsub("\n"; "\\n")
  | gsub("\t"; "\\t")) as $fields |
$local_time + " " + $level + " [0] " + $level
+ " - " + $query_id + " - " + $message
+ " | target=" + (($row[2] // "-") | tostring)
+ " node_id=" + (($row[5] // "-") | tostring)
+ " warehouse_id=" + (($row[6] // "-") | tostring)
+ " path=" + (($row[1] // "-") | tostring)
+ " cluster_id=" + (($row[4] // "-") | tostring)
+ " batch_number=" + (($row[10] // "-") | tostring)
+ " fields=" + $fields
