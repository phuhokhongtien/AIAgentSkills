using Microsoft.EntityFrameworkCore;
using SampleApi.Data;
using SampleApi.Models;

namespace SampleApi.Services;

public interface IDebugTestService
{
    Task<List<User>> GetUsersWithOrdersN1Async();
    Task<List<User>> GetUsersWithOrdersOptimalAsync();
    Task<List<User>> SlowSearchAsync(string q);
    Task<User?> GetHealthyUserAsync(int id);
}

public class DebugTestService : IDebugTestService
{
    private readonly AppDbContext _db;
    private readonly ILogger<DebugTestService> _logger;

    public DebugTestService(AppDbContext db, ILogger<DebugTestService> logger)
    {
        _db = db;
        _logger = logger;
    }

    public async Task<List<User>> GetUsersWithOrdersN1Async()
    {
        _logger.LogInformation("N+1 endpoint: loading users, then orders per user (intentional N+1)");

        var users = await _db.Users.AsNoTracking().ToListAsync();

        foreach (var u in users)
        {
            u.Orders = await _db.Orders.AsNoTracking()
                .Where(o => o.UserId == u.Id)
                .ToListAsync();
        }

        return users;
    }

    public async Task<List<User>> GetUsersWithOrdersOptimalAsync()
    {
        _logger.LogInformation("Optimal endpoint: single JOIN via .Include");

        return await _db.Users
            .AsNoTracking()
            .Include(u => u.Orders)
            .ToListAsync();
    }

    public async Task<List<User>> SlowSearchAsync(string q)
    {
        _logger.LogInformation("Slow search endpoint: artificial delay + LIKE query");

        await Task.Delay(150);

        return await _db.Users
            .AsNoTracking()
            .Where(u => EF.Functions.Like(u.Name, $"%{q}%"))
            .ToListAsync();
    }

    public async Task<User?> GetHealthyUserAsync(int id)
    {
        _logger.LogInformation("Healthy endpoint: single user lookup by id={Id}", id);

        return await _db.Users
            .AsNoTracking()
            .FirstOrDefaultAsync(u => u.Id == id);
    }
}
