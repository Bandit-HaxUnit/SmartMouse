import json

def main():
    with open("mousedata_parsed_cleaned.json", "r") as f:
        data = json.load(f)

    total = 0

    for threshold_str, directions_dict in data.items():
        print(f"Threshold: {threshold_str}")
        for direction, offset_arrays in directions_dict.items():
            count = len(offset_arrays)
            total += count
            print(f"  {direction}: {count}")
        print()

    print(f"Total samples: {total}")

if __name__ == "__main__":
    main()