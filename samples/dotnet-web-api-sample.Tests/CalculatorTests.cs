using Xunit;

namespace SampleTests;

public class CalculatorTests
{
    [Fact]
    public void Add_ReturnsSum()
    {
        Assert.Equal(5, Calculator.Add(2, 3));
    }

    [Fact]
    public void Subtract_ReturnsDifference()
    {
        Assert.Equal(1, Calculator.Subtract(3, 2));
    }

    // Demo FAILURE: Calculator.Divide is buggy (returns 0).
    [Fact]
    public void Divide_ReturnsQuotient()
    {
        Assert.Equal(2, Calculator.Divide(10, 5));
    }

    // Demo SKIPPED.
    [Fact(Skip = "Pending: edge cases for negative operands not implemented yet")]
    public void IsEven_HandlesNegatives()
    {
        Assert.True(Calculator.IsEven(-4));
    }

    [Theory]
    [InlineData(2, true)]
    [InlineData(7, false)]
    public void IsEven_Works(int n, bool expected)
    {
        Assert.Equal(expected, Calculator.IsEven(n));
    }
}
