import launch

if not launch.is_installed("requests-cache"):
    launch.run_pip("install requests-cache", "requests-cache")
