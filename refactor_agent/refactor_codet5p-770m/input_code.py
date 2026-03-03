
def add(a, b):
    return a + b

def multiply(x, y):
    result = x * y
    return result

def process_data(items, discount, tax):
    total = 0
    for item in items:
        total += item['price']
    if discount:
        total *= 0.9
    if tax:
        total *= 1.08
    return total
