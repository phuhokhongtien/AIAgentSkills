using SampleApi.Models;

namespace SampleApi.Data;

public static class DbSeeder
{
    public static void Seed(AppDbContext db)
    {
        db.Database.EnsureCreated();

        if (db.Users.Any()) return;

        var users = new List<User>();
        for (int i = 1; i <= 20; i++)
        {
            users.Add(new User
            {
                Id = i,
                Name = $"User {i:D2}",
                Email = $"user{i:D2}@example.com",
                IsActive = i % 3 != 0
            });
        }
        db.Users.AddRange(users);
        db.SaveChanges();

        var rng = new Random(42);
        var products = new[] { "Widget", "Gadget", "Doohickey", "Thingamajig", "Whatsit" };
        var orders = new List<Order>();
        int orderId = 1;
        foreach (var user in users)
        {
            for (int j = 0; j < 5; j++)
            {
                orders.Add(new Order
                {
                    Id = orderId++,
                    UserId = user.Id,
                    Product = products[rng.Next(products.Length)] + " " + (char)('A' + j),
                    Amount = (decimal)Math.Round(rng.NextDouble() * 200 + 10, 2)
                });
            }
        }
        db.Orders.AddRange(orders);
        db.SaveChanges();
    }
}
