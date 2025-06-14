const pathfinder = require("mineflayer-pathfinder").pathfinder;
const Movements = require("mineflayer-pathfinder").Movements;
const { GoalXZ } = require("mineflayer-pathfinder").goals;
const mineflayerViewer = require("prismarine-viewer").headless;
const { workerData, parentPort } = require("worker_threads");
const utils = require("./utils");
const { default: logger } = require("./logger");

/**
 * Find next coordinate to walk to
 * @param {number} currentX x-coordinate
 * @param {number} currentZ z-coordinate
 * @returns {GoalXZ} next walking position
 */
function nextGoal(currentX, currentZ) {
  let x = currentX + utils.getRandomIntInterval(50) - workerData.box_width / 2;
  let z = currentZ + utils.getRandomIntInterval(50) - workerData.box_width / 2;
  /*
  let ts = Date.now() / 1000;
  console.log(
    `${ts} - bot ${bot.username}, ${bot.entity.position}, ${v(
      x,
      bot.entity.position.y,
      z,
    )}`,
  );
  */
  return new GoalXZ(x, z);
}

/**
 * Video Recording function
 * video will be saved in the videos directory in project root
 */
const hostname = process.env.HOSTNAME;
const workload = process.env.WORKLOAD || "walk";
const username = workerData.username;
function recordBotInFirstPerson(bot, _) {
  bot.once("spawn", () => {
    mineflayerViewer(bot, {
      output: `../videos/${hostname}-${workload}-${username}-${utils.getTimestamp()}.mp4`,
      frames: (utils.get_time_left() / 1000) * 60,
      width: 512,
      height: 512,
    });
  });
}

function walk(bot, _) {
  const beginWalking = async () => {
    // first teleport to a location
    bot.chat(
      `/tp ${username} ${workerData.spawn_x} ${workerData.spawn_y} ${workerData.spawn_z}`,
    );
    // set spawn point to the given location
    bot.chat(
      `/minecraft:spawnpoint @s ${workerData.spawn_x} ${workerData.spawn_y} ${workerData.spawn_z}`,
    );
    bot.loadPlugin(pathfinder);

    let defaultMove = new Movements(bot);
    defaultMove.allowSprinting = false;
    defaultMove.canDig = true;
    defaultMove.allowParkour = true;
    defaultMove.allowFreeMotion = true;
    bot.pathfinder.setMovements(defaultMove);

    var goal = nextGoal(workerData.spawn_z, workerData.spawn_z);
    bot.pathfinder.setGoal(goal);

    bot.on("goal_reached", () => {
      goal = nexGoal(goal.x, goal.z);
      bot.pathfinder.setGoal(goal);
    });
  };
  // log bot position every 0.5 seconds
  setInterval(() => {
    try {
      parentPort.postMessage(
        `${username}:${bot.entity.position.x}-${bot.entity.position.y}`,
      );
    } catch {
      console.log("Error: could not post bot.entity.position.x/y to master");
    }
  }, 500);

  bot.once("spawn", beginWalking);
}

function run() {
  const plugins = {
    walk,
  };

  if (workerData.record) {
    plugins.recordBotInFirstPerson = recordBotInFirstPerson;
  }

  const worker_bot = utils.createBot(workerData.username, plugins);

  worker_bot.on("kicked", console.log);
  worker_bot.on("error", console.log);
}

run();
