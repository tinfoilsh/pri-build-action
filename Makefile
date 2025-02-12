all: clean build run

clean:
	rm -rf output

build:
	docker build -t tinfoil-builder .

run:
	rm -rf output && mkdir output
	docker run --rm -it \
		-v $(PWD)/config.yml:/config.yml \
		-v $(PWD)/cache:/cache \
		-v $(PWD)/output:/output tinfoil-builder
