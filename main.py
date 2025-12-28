from coordinator.orchestrator import Coordinator


def main():
     with open("sample.py", "r") as f:
        sample_code = f.read()
    

     coordinator = Coordinator()
     coordinator.run(sample_code)


if __name__ == "__main__":
    main()
