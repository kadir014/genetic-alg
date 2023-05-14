from random import randint, random

import pygame


# Window settings
WINDOW_WIDTH = 720
WINDOW_HEIGHT = 720
UNIT = 100 # 100 pixels = 1 meter

# Physics simulation settings
FPS = 60
HZ = 1 / FPS
GRAVITY = 9.81
AIR_FRICTION = 0.008
SHOT_DURATION = 7.0
MUTATION_CHANCE = 0.0


# Pygame stuff
pygame.init()
window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Ghast's Genetic Algorithm Challenge")
clock = pygame.time.Clock()

# Load assets
font = pygame.Font("assets/FiraCode.ttf")

net_image = pygame.transform.smoothscale_by(
    pygame.image.load("assets/net.png").convert_alpha(), 0.65)

basketball_frames = [
    pygame.transform.smoothscale_by(
        pygame.image.load(f"assets/frames/frame_{str(i).zfill(3)}.png").convert_alpha(),
        0.32
    )
    for i in range(165)
]


class Basketball:
    """
    Bouncy orange ball.
    """

    def __init__(self, position: pygame.Vector2):
        self.position = position
        self.velocity = pygame.Vector2(0)
        self.force = pygame.Vector2(0)

        # NBA basketball is 0.625 kg and 12.1cm in radius
        # But I multiply radius by 4 just for visuality's sake
        self.mass = 0.625
        self.invmass = 1 / self.mass
        self.radius = 0.121 * 4
        self.elasticity = 0.8

        self.fframe = 0.0
        self.frame = 0

    def create_genes(self):
        """ Create random genes. """

        self.gene_i = 0

        self.gene_dir = []
        self.gene_strength = []

        # 3 shots
        for _ in range(3):
            self.gene_dir.append(randint(0, 359))
            self.gene_strength.append(randint(65, 2300))

    def apply_gene(self):
        if self.gene_i == len(self.gene_dir): return

        self.force = pygame.Vector2(1, 0).rotate(self.gene_dir[self.gene_i]) * self.gene_strength[self.gene_i]

        self.gene_i += 1

    @property
    def fitness(self) -> float:
        """ Calculate fitness of the ball. """

        fitness = (self.position - pygame.Vector2(5.85, 2.6)).length()

        if fitness > 7: fitness = 7

        fitness = (7 - fitness) / 7

        return fitness

    def update(self, dt: float):
        """ Update ball physics. """

        # Integrate linear acceleration
        acceleration = self.force * self.invmass + pygame.Vector2(0, GRAVITY)
        self.velocity += acceleration * dt

        # Resolve collisions
        future_vel = self.velocity * dt

        if self.position.x + future_vel.x - self.radius < 0 or \
           self.position.x + future_vel.x + self.radius > WINDOW_WIDTH / UNIT:
            self.velocity.x  *= -self.elasticity

        if self.position.y + future_vel.y - self.radius < 0 or \
           self.position.y + future_vel.y + self.radius > WINDOW_HEIGHT / UNIT:
            self.velocity.y *= -self.elasticity

        net = pygame.Vector2(max(5.3, self.position.x), 3.2)
        dist = (net - (self.position + future_vel)).length()
        radii = self.radius + 0.3

        if dist <= radii:
            normal = (net - self.position).normalize()
            self.velocity = self.velocity.reflect(normal) * self.elasticity

        # Apply friction / damping
        self.velocity *= (1 - AIR_FRICTION)

        # Integrate linear velocity
        self.position += self.velocity * dt

        # Reset force
        self.force = pygame.Vector2(0)

    def draw(self, surface: pygame.Surface):
        """ Draw the ball animation on the surface. """

        # Draw the glow
        pygame.draw.circle(
            surface,
            pygame.Color(255, 0, 0).lerp(pygame.Color(0, 255, 0), self.fitness),
            self.position * UNIT + pygame.Vector2(1, 1),
            self.radius * 100 + 5
        )

        # Draw the current frame
        frame_surf = basketball_frames[int(self.frame)]
        surface.blit(frame_surf, self.position * UNIT - frame_surf.get_rect().center)

        self.fframe += self.velocity.x
        self.frame = int(self.fframe) % len(basketball_frames)


class Generation:
    def __init__(self, population: int):

        # Create population
        self.population = [
            Basketball(pygame.Vector2(50 / UNIT, 650 / UNIT))
            for _ in range(population)
        ]

        # Create genes
        for ball in self.population:
            ball.create_genes()

        # Apply first gene
        self.last_gene = 0
        for ball in self.population:
            ball.apply_gene()

    def highest_fitness(self) -> float:
        """ Get the highest fitness in the population. """

        fitness_vals = [ball.fitness for ball in self.population]

        return list(sorted(fitness_vals))[-1]
    
    def winner(self) -> Basketball:
        """ Get the ball with the highest fitness. """

        highest = self.highest_fitness()

        for ball in self.population:
            if ball.fitness == highest:
                return ball

    def update(self, dt: float) -> bool:
        """ Update the population. """

        # Apply the next gene if applicable
        self.last_gene += 1
        if self.last_gene > FPS * SHOT_DURATION:
            self.last_gene = 0

            # If all shots are done this generation is finished
            if self.population[0].gene_i == 3: return True

            for ball in self.population:
                ball.apply_gene()


        for ball in self.population:
            ball.update(dt)

        return False

    def draw(self, surface: pygame.Surface):
        """ Draw the population. """

        for ball in self.population:
            ball.draw(surface)


class Solver:
    def __init__(self, population: int):
        self.population = population
        self.generation = Generation(self.population)
        self.generation_n = 0

    def next_generation(self):
        """ Create a new generation and inherit the genes. """

        winner = self.generation.winner()

        self.generation = Generation(self.population)
        self.generation_n += 1

        # Overwrite genes
        for ball in self.generation.population:
            gene_dir = []
            gene_strength = []

            for i in range(3):
                # Inherit winner genes by chance
                if random() < 0.75:

                    # Mutate genes

                    if random() < MUTATION_CHANCE:
                        gene_dir.append(randint(0, 359))
                    else:
                        gene_dir.append(winner.gene_dir[i])

                    if random() < MUTATION_CHANCE:
                        gene_strength.append(randint(65, 2300))
                    else:
                        gene_strength.append(winner.gene_strength[i])

                else:
                    gene_dir.append(randint(0, 359))
                    gene_strength.append(randint(65, 2300))

            ball.gene_dir = gene_dir
            ball.gene_strength = gene_strength

    def update(self, dt: float):
        """ Update solver. """

        is_done = self.generation.update(dt)

        if is_done:
            print(f"Generation {self.generation_n} highest fitness: {round(self.generation.highest_fitness(), 3)}")
            self.next_generation()


solver = Solver(5)


# Main loop
while True:
    clock.tick(60)
    pygame.display.set_caption(f"Ghast's Genetic Algorithm Challenge @{round(clock.get_fps())}FPS")

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            raise SystemExit(0)
        
    solver.update(HZ)
        
    window.fill((255, 255, 255))

    solver.generation.draw(window)

    window.blit(net_image, (WINDOW_WIDTH - net_image.get_width(), 300))

    # UI
    window.blit(font.render(f"Generation: {solver.generation_n}", True, (27, 30, 41)), (5, 5))
    window.blit(font.render(f"Population: {solver.population}", True, (27, 30, 41)), (5, 30))
    window.blit(font.render(f"Fitness:    {round(solver.generation.highest_fitness(), 3)}", True, (27, 30, 41)), (5, 55))

    pygame.display.flip()