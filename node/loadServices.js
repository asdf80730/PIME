'use strict';

let fs   = require('fs');
let path = require('path');


// `baseDir` defaults to the process working directory, which is what the
// backend uses at runtime. Tests pass a fixture directory instead.
function loadServices(baseDir) {
  baseDir = baseDir || process.cwd();
  let imeDir = fs.readdirSync(path.join(baseDir, 'input_methods'));
  let services = [];

  imeDir.forEach((dir) => {

    if (fs.lstatSync(path.join(baseDir, 'input_methods', dir)).isDirectory()) {
      let configFile = fs.readFileSync(path.join(baseDir, 'input_methods', dir, 'ime.json'), 'utf8');
      let config = JSON.parse(configFile);
      let textService = require(path.join(baseDir, 'input_methods', dir, config.moduleName));

      config['textService'] = textService;

      services.push(config);
    }
  });

  return services;
}

function loadServiceById(id, baseDir) {
  baseDir = baseDir || process.cwd();
  let imeDir = fs.readdirSync(path.join(baseDir, 'input_methods'));
  let service = null;

  imeDir.forEach((dir) => {

    if (fs.lstatSync(path.join(baseDir, 'input_methods', dir)).isDirectory()) {
      let configFile = fs.readFileSync(path.join(baseDir, 'input_methods', dir, 'ime.json'), 'utf8');
      let config = JSON.parse(configFile);

      if (config['guid'].toLowerCase() === id.toLowerCase()) {
        service = require(path.join(baseDir, 'input_methods', dir, config.moduleName));
      }
    }
  });

  return service;
}

module.exports = {
  loadServices,
  loadServiceById
};
