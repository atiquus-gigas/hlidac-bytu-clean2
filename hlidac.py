from sources.dummy import fetch as fetch_dummy

def main():
    print("Spouštím hlídač bytů...")
    results = fetch_dummy()
    print("Výsledky:", results)

if __name__ == "__main__":
    main()
