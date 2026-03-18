.PHONY: setup setup-python setup-remotion clean

setup: setup-python setup-remotion
	@echo "Done. Run 'videvide script.yaml' to start."

setup-python:
	pip install -e .

setup-remotion:
	cd remotion && npm install
	@echo "Remotion ready."

clean:
	rm -rf output/audio output/subs output/effects
	rm -f output/project.kdenlive
