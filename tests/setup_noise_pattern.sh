# If no arguments are passed, take it as a reset command.
if [ "$#" -eq 0 ]; then
    echo "Clearing the test pattern on the detector."

elif [ "$#" -eq 1 ]; then
    echo "Setting test pattern from file ""$1"
    sls_detector_put trimbits "$1"
    echo "Test pattern setting finished. Inspect output above."
else
    echo "Invalid number of parameters. Usage:"
    echo "    $0 : clear the current test pattern."
    echo "    $0 noise_pattern_file : set the noise test pattern."
fi
