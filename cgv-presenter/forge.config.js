const { FusesPlugin } = require('@electron-forge/plugin-fuses');
const { FuseV1Options, FuseVersion } = require('@electron/fuses');
const fs = require('fs');
const path = require('path');

const macEntitlements = path.resolve(__dirname, 'build', 'entitlements.mac.plist');
const appIcon = path.resolve(__dirname, 'assets', 'cgv-app-icon');
const cgvDataBibles = path.resolve(__dirname, '..', '..', 'cgv-data', 'bibles');
const cgvDataMorphology = path.resolve(__dirname, '..', '..', 'cgv-data', 'morphology');
const cgvDataInterlinears = path.resolve(__dirname, '..', '..', 'cgv-data', 'interlinears');
const bundledBibles = fs.existsSync(cgvDataBibles)
  ? cgvDataBibles
  : path.resolve(__dirname, 'bibles');
const bundledMorphology = fs.existsSync(path.join(cgvDataMorphology, 'MorphGNT'))
  ? cgvDataMorphology
  : "";
const bundledInterlinears = fs.existsSync(path.join(cgvDataInterlinears, 'NT'))
  ? cgvDataInterlinears
  : "";

module.exports = {
  packagerConfig: {
    name: 'CGV Presenter',
    asar: true,
    icon: appIcon,
    osxSign: {
      identity: '-',
      identityValidation: false,
      preAutoEntitlements: false,
      optionsForFile: () => ({
        entitlements: macEntitlements,
        hardenedRuntime: false,
      }),
    },
    extraResource: [
      bundledBibles,
      ...(bundledMorphology ? [bundledMorphology] : []),
      ...(bundledInterlinears ? [bundledInterlinears] : []),
      path.resolve(__dirname, 'courses', 'Romanos'),
      path.resolve(__dirname, 'songs'),
    ],
  },
  rebuildConfig: {},
  makers: [
    {
      name: '@electron-forge/maker-squirrel',
      platforms: ['win32'],
      config: {
        name: 'CGV.Presenter',
        authors: 'Cultivados en Gracia y Verdad',
        description: 'Offline-first presentation and training delivery app for Cultivados en Gracia y Verdad courses.',
        setupIcon: path.resolve(__dirname, 'assets', 'cgv-app-icon.ico'),
      },
    },
    {
      name: '@electron-forge/maker-zip',
      platforms: ['darwin'],
    },
    {
      name: '@electron-forge/maker-deb',
      config: {},
    },
    {
      name: '@electron-forge/maker-rpm',
      config: {},
    },
  ],
  plugins: [
    {
      name: '@electron-forge/plugin-auto-unpack-natives',
      config: {},
    },
    new FusesPlugin({
      version: FuseVersion.V1,
      [FuseV1Options.RunAsNode]: false,
      [FuseV1Options.EnableCookieEncryption]: true,
      [FuseV1Options.EnableNodeOptionsEnvironmentVariable]: false,
      [FuseV1Options.EnableNodeCliInspectArguments]: false,
      [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: false,
      [FuseV1Options.OnlyLoadAppFromAsar]: false,
    }),
  ],
  hooks: {
    postMake: async (_forgeConfig, makeResults) => {
      const builtForMac = makeResults.some(result => result.platform === 'darwin');
      if (!builtForMac || process.platform !== 'darwin') {
        return makeResults;
      }

      require('./scripts/build-macos-release');
      return makeResults;
    },
  },
};
