import sys
import yaml
from parser import expand

def main():
    if len(sys.argv) < 2:
        print("Usage: videvide <script.yaml>")
        sys.exit(1)

    script_path = sys.argv[1]

    with open(script_path) as f:
        script = yaml.safe_load(f)

    expanded = expand(script)
    print(yaml.dump(expanded, default_flow_style=False))

if __name__ == "__main__":
    main()
