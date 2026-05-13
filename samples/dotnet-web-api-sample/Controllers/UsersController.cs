using Microsoft.AspNetCore.Mvc;
using SampleApi.Models;
using SampleApi.Services;

namespace SampleApi.Controllers;

[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    private readonly IUserService _userService;
    private readonly ILogger<UsersController> _logger;

    public UsersController(IUserService userService, ILogger<UsersController> logger)
    {
        _userService = userService;
        _logger = logger;
    }

    /// <summary>
    /// Get all users.
    /// Bug: N+1 queries — loads orders per-user individually.
    /// Test: curl http://localhost:5000/api/users
    /// </summary>
    [HttpGet]
    public async Task<IActionResult> GetAll()
    {
        _logger.LogInformation("GET /api/users called");
        var users = await _userService.GetAllAsync();
        return Ok(users);
    }

    /// <summary>
    /// Get user by ID.
    /// Bug: throws InvalidCastException for non-integer IDs (e.g. "abc").
    /// Test (works):  curl http://localhost:5000/api/users/1
    /// Test (breaks): curl http://localhost:5000/api/users/abc
    /// </summary>
    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(string id)
    {
        _logger.LogInformation("GET /api/users/{Id} called", id);
        try
        {
            var user = await _userService.GetByIdAsync(id);
            return Ok(user);
        }
        catch (KeyNotFoundException ex)
        {
            _logger.LogWarning("User not found: {Message}", ex.Message);
            return NotFound(new { error = ex.Message });
        }
    }

    /// <summary>
    /// Update a user.
    /// Bug: throws InvalidCastException for non-integer IDs.
    /// Test (works):  curl -X PUT http://localhost:5000/api/users/1 -H "Content-Type: application/json" -d '{"name":"Alice Updated"}'
    /// Test (breaks): curl -X PUT http://localhost:5000/api/users/abc -H "Content-Type: application/json" -d '{"name":"Test"}'
    /// </summary>
    [HttpPut("{id}")]
    public async Task<IActionResult> Update(string id, [FromBody] UpdateUserRequest request)
    {
        _logger.LogInformation("PUT /api/users/{Id} called", id);
        var user = await _userService.UpdateAsync(id, request);
        return Ok(user);
    }
}
