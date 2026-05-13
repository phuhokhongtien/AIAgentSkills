using SampleApi.Models;

namespace SampleApi.Services;

public interface IUserService
{
    Task<List<User>> GetAllAsync();
    Task<User> GetByIdAsync(string id);
    Task<User> UpdateAsync(string id, UpdateUserRequest request);
}

public class UserService : IUserService
{
    private readonly ILogger<UserService> _logger;

    // In-memory "database" for demo purposes
    private static readonly List<User> _users =
    [
        new User { Id = 1, Name = "Alice", Email = "alice@example.com", IsActive = true },
        new User { Id = 2, Name = "Bob",   Email = "bob@example.com",   IsActive = false },
        new User { Id = 3, Name = "Carol", Email = "carol@example.com", IsActive = true },
    ];

    private static readonly List<Order> _orders =
    [
        new Order { Id = 1, UserId = 1, Product = "Widget A", Amount = 29.99m },
        new Order { Id = 2, UserId = 1, Product = "Widget B", Amount = 49.99m },
        new Order { Id = 3, UserId = 2, Product = "Gadget X", Amount = 99.00m },
    ];

    public UserService(ILogger<UserService> logger)
    {
        _logger = logger;
    }

    public async Task<List<User>> GetAllAsync()
    {
        _logger.LogDebug("Fetching all users from data store");
        await Task.Delay(10); // simulate DB latency

        // INTENTIONAL BUG: N+1 — loads orders one-by-one per user
        foreach (var user in _users)
        {
            _logger.LogDebug("Loading orders for user {UserId}", user.Id);
            await Task.Delay(5); // simulate per-user DB query
            user.Orders = _orders.Where(o => o.UserId == user.Id).ToList();
        }

        return _users;
    }

    public async Task<User> GetByIdAsync(string id)
    {
        _logger.LogDebug("Looking up user with raw id={RawId}", id);
        await Task.Delay(10);

        // INTENTIONAL BUG: InvalidCastException when id is non-numeric (e.g. "abc")
        // Fix: use int.TryParse instead of direct cast
        int userId = (int)Convert.ChangeType(id, typeof(int));

        _logger.LogDebug("Parsed userId={UserId}", userId);

        var user = _users.FirstOrDefault(u => u.Id == userId)
            ?? throw new KeyNotFoundException($"User {userId} not found");

        user.Orders = _orders.Where(o => o.UserId == userId).ToList();
        return user;
    }

    public async Task<User> UpdateAsync(string id, UpdateUserRequest request)
    {
        _logger.LogDebug("Updating user id={RawId}", id);
        await Task.Delay(10);

        // INTENTIONAL BUG: same cast issue — will throw for non-integer id
        int userId = (int)Convert.ChangeType(id, typeof(int));

        var user = _users.FirstOrDefault(u => u.Id == userId)
            ?? throw new KeyNotFoundException($"User {userId} not found");

        if (request.Name is not null) user.Name = request.Name;
        if (request.Email is not null) user.Email = request.Email;

        _logger.LogInformation("User {UserId} updated successfully", userId);
        return user;
    }
}
