using Microsoft.AspNetCore.Mvc;
using SampleApi.Services;

namespace SampleApi.Controllers;

[ApiController]
[Route("api")]
public class DebugTestController : ControllerBase
{
    private readonly IDebugTestService _service;
    private readonly ILogger<DebugTestController> _logger;

    public DebugTestController(IDebugTestService service, ILogger<DebugTestController> logger)
    {
        _service = service;
        _logger = logger;
    }

    [HttpGet("users-with-orders")]
    public async Task<IActionResult> UsersWithOrdersN1()
    {
        _logger.LogInformation("GET /api/users-with-orders (N+1 demo)");
        var users = await _service.GetUsersWithOrdersN1Async();
        return Ok(users);
    }

    [HttpGet("users-with-orders-optimal")]
    public async Task<IActionResult> UsersWithOrdersOptimal()
    {
        _logger.LogInformation("GET /api/users-with-orders-optimal (single-JOIN)");
        var users = await _service.GetUsersWithOrdersOptimalAsync();
        return Ok(users);
    }

    [HttpGet("slow-search")]
    public async Task<IActionResult> SlowSearch([FromQuery] string q = "User")
    {
        _logger.LogInformation("GET /api/slow-search?q={Q} (slow query demo)", q);
        var users = await _service.SlowSearchAsync(q);
        return Ok(users);
    }

    [HttpGet("healthy-user/{id:int}")]
    public async Task<IActionResult> HealthyUser(int id)
    {
        _logger.LogInformation("GET /api/healthy-user/{Id} (single-query healthy path)", id);
        var user = await _service.GetHealthyUserAsync(id);
        if (user is null) return NotFound(new { error = $"User {id} not found" });
        return Ok(user);
    }
}
