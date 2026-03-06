class Calculator:
    """
    A simple calculator class.
    """

    def add(self, a, b):
        """Add two numbers."""
        return a + b

    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b


def compute_statistics(numbers):
    """
    Compute basic statistics for a list of numbers.
    """

    total = 0
    count = 0

    for n in numbers:
        total += n
        count += 1

    if count == 0:
        return None

    mean = total / count

    # intentionally a bit long to trigger smell detection
    variance_sum = 0
    for n in numbers:
        variance_sum += (n - mean) ** 2

    variance = variance_sum / count

    return {
        "mean": mean,
        "variance": variance
    }


def format_result(stats):
    """
    Format the statistics dictionary into a readable string.
    """

    if stats is None:
        return "No data available."

    result = "Statistics:\n"
    result += f"Mean: {stats['mean']}\n"
    result += f"Variance: {stats['variance']}"

    return result