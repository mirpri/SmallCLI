#!/usr/bin/env node

import axios from 'axios';
import inquirer from 'inquirer';
import chalk from 'chalk';
import ora from 'ora';
import { exec, spawn } from 'child_process';
import fs from 'fs/promises';
import util from 'util';

const execPromise = util.promisify(exec);
const SERVER_URL = 'http://localhost:8000';

async function main() {
  console.log(chalk.bold.blue('Welcome to Small CLI Agent'));

  // 1. Get Task Description
  const { taskDescription } = await inquirer.prompt([
    {
      type: 'input',
      name: 'taskDescription',
      message: 'What would you like me to do?',
      validate: (input) => input.trim() !== '' ? true : 'Please enter a task description.',
    },
  ]);

  const spinner = ora('Gathering system info...').start();
  let systemInfo = "Unknown System";
  try {
      const { stdout } = await execPromise('cat /etc/os-release || uname -a');
      systemInfo = stdout.trim();
  } catch (e) {
      // Ignore error, use default
  }
  spinner.text = 'Initializing agent...';

  try {
    // 2. Start Agent
    const startResponse = await axios.post(`${SERVER_URL}/agent/start`, {
      description: taskDescription,
      system_info: systemInfo
    });

    let currentState = startResponse.data;
    spinner.stop();

    // 3. Main Loop
    while (currentState.status !== 'completed' && currentState.status !== 'aborted') {
      currentState = await handleState(currentState);
    }

    if (currentState.status === 'completed') {
      console.log(chalk.green('\nTask Completed Successfully!'));
    } else {
      console.log(chalk.red('\nTask Aborted.'));
    }

  } catch (error) {
    spinner.stop();
    console.error(chalk.red('\nError communicating with server:'), error.message);
    if (error.response) {
        console.error(chalk.yellow('Server Response:'), error.response.data);
    }
  }
}

async function handleState(state) {
  const { thread_id, status, plan, pending_action, next_step } = state;

  console.log(chalk.dim(`\n[Thread: ${thread_id.substring(0, 8)}...] Status: ${status}`));

  if (status === 'waiting_for_plan_approval') {
    console.log(chalk.bold.cyan('\nProposed Plan:'));
    plan.forEach((step, index) => {
      console.log(chalk.white(`  ${index + 1}. ${step}`));
    });

    const { approved } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'approved',
        message: 'Do you approve this plan?',
        default: true,
      },
    ]);

    return await sendApproval(thread_id, approved);
  }

  if (status === 'waiting_for_command_approval') {
    console.log(chalk.bold.yellow('\nPending Command Execution:'));
    console.log(chalk.white(`  $ ${pending_action.command}  `));

    const { approved } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'approved',
        message: 'Execute this command locally?',
        default: true,
      },
    ]);

    if (!approved) {
        return await sendApproval(thread_id, false);
    }

    let output = '';
    let success = false;
    
    console.log(chalk.gray('--- Output ---'));
    try {
        output = await runCommand(pending_action.command);
        success = true;
        console.log(chalk.gray('--------------'));
        console.log(chalk.green('Command executed successfully'));
    } catch (error) {
        output = error.output || error.message;
        success = false;
        console.log(chalk.gray('--------------'));
        console.log(chalk.red('Command execution failed'));
    }

    return await sendApproval(thread_id, true, output, success);
  }

  if (status === 'waiting_for_edit_approval') {
    console.log(chalk.bold.yellow('\nPending File Edit:'));
    console.log(chalk.white(`  File: ${pending_action.details.filename}`));
    console.log(chalk.dim('  (Content preview hidden for brevity)'));

    const { approved } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'approved',
        message: 'Apply this file edit locally?',
        default: true,
      },
    ]);

    if (!approved) {
        return await sendApproval(thread_id, false);
    }

    let output = '';
    let success = false;
    const spinner = ora('Writing file...').start();

    try {
        await fs.writeFile(pending_action.details.filename, pending_action.details.content, 'utf8');
        output = 'File written successfully';
        success = true;
        spinner.succeed('File written successfully');
    } catch (error) {
        output = error.message;
        success = false;
        spinner.fail('File write failed');
    }

    return await sendApproval(thread_id, true, output, success);
  }
  
  // If running or other states, poll
  const spinner = ora('Agent is working...').start();
  // Simple polling delay
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  try {
      const response = await axios.get(`${SERVER_URL}/agent/${thread_id}`);
      spinner.stop();
      return response.data;
  } catch (e) {
      spinner.stop();
      throw e;
  }
}

async function sendApproval(threadId, approved, executionOutput = null, executionSuccess = false) {
  const spinner = ora(approved ? 'Resuming execution...' : 'Aborting...').start();
  const payload = {
    thread_id: threadId,
    approved: approved,
  };
  
  if (executionOutput !== null) {
      payload.execution_output = executionOutput;
      payload.execution_success = executionSuccess;
  }
  
  const response = await axios.post(`${SERVER_URL}/agent/approve`, payload);
  spinner.stop();
  return response.data;
}

function runCommand(command) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, { shell: true });
    let output = '';

    child.stdout.on('data', (data) => {
      process.stdout.write(data);
      output += data.toString();
    });

    child.stderr.on('data', (data) => {
      process.stderr.write(data);
      output += data.toString();
    });

    child.on('close', (code) => {
      if (code === 0) {
        resolve(output);
      } else {
        const error = new Error(`Command failed with code ${code}`);
        error.output = output;
        reject(error);
      }
    });

    child.on('error', (err) => {
      reject(err);
    });
  });
}

main();
