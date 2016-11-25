class MyCSVString:
    def __init__(self, item='', delimiter=',', quote='"'):
        self.delimiter = delimiter
        self.quote = quote
        self.string = ''
        if item != '':
            self.string = quote + str(item).replace('\n', '\\n') + quote

    def write(self, item):
        if self.string == '':
            self.string += self.quote + str(item).replace('\n', '\\n') + self.quote
        else:
            self.string += self.delimiter + self.quote + str(item).replace('\n', '\\n') + self.quote

    def end_line(self):
        self.string += '\n'




# this function is meant to count the length of an array recursively
def recursive_length(array = [], length = 0):
    # base case
    if len(array) == 0:
        return length

    # recursive call on list in list
    item = array.pop(0)
    if isinstance(item, list):
        new_length = recursive_length(item, length)
        return recursive_length(array, new_length)

    # recursive call on object in list
    return recursive_length(array, length + 1)


# this function is meant to write a csv style string of an array, including the length of each sub array
def write_array_to_csv(array = [], csvstr = MyCSVString(), length = 0):
    # base case
    if len(array) == 0:
        return csvstr, length

    item = array.pop(0) # get the item we will write

    # prepare for recursion on a list
    if isinstance(item, list):
        csvstr.write(len(item))  # write the number of items in this array for reading (this is a sub item)
        new_csvstr, new_length  = write_array_to_csv(item, csvstr, length)
        return write_array_to_csv(array, new_csvstr, new_length)

    # item is not a list
    length += 1
    csvstr.write(item)

    # preparefor recursion on an object
    return write_array_to_csv(array, csvstr, length)


# this function is meant to write a dictionary of objects or arrays to a csv type string and return it
def write_to_csv(ability_dict = {}, csvstr = MyCSVString()):
    # base case
    if not ability_dict:
        return csvstr

    key, value = ability_dict.popitem() # get what we want to be writing

    # if it's a list, recursive write the list data
    if isinstance(value, list):
        csvstr.write(key)
        my_csv, length = write_array_to_csv(value, MyCSVString())
        csvstr.write(length)  # write the number of items that we'll be writing
        csvstr.write(my_csv.string[1:-1])  # write the array to the csv string (remove the 1st and last quotation)
        return write_to_csv(ability_dict, csvstr)  # recurse on the rest of the dictionary

    # it's not a list (it's a dictionary)
    csvstr.write(key)  # we want to write the name/ability name
    csvstr.write(len(value))  # write the number of abilities (otr data objects) we're about to write
    new_csvstr = write_to_csv(value, csvstr)  # get the new csv str from the value (the dictionary)
    return write_to_csv(ability_dict, new_csvstr)  # recurse on the rest of the dicionary and the new csv string