namespace SampleTests;

// Tiny unit under test so coverage has something to measure.
public static class Calculator
{
    public static int Add(int a, int b) => a + b;

    public static int Subtract(int a, int b) => a - b;

    // Intentionally buggy: returns 0 instead of the quotient.
    // Drives the demo assertion failure + root-cause analysis.
    public static int Divide(int a, int b) => 0;

    public static bool IsEven(int n) => n % 2 == 0;
}
