# open image, put your image here
with open("assets/pickachu.pbm", "rb") as f:
    f.readline()  # number
    f.readline()  # Creator
    f.readline()  # Dimensions
    data = bytearray(f.read())
    print(data)
