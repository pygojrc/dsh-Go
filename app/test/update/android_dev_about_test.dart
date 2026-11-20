import 'package:dsh_app/state/android_features.dart';
import 'package:dsh_app/state/app_info.dart';
import 'package:dsh_app/state/update_state.dart';
import 'package:dsh_app/ui/settings/about_page.dart';
import 'package:dsh_app/ui/update/update_tiles.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../shell/golden_harness.dart';

void main() {
  testWidgets('Android 关于页显示开发版后缀且不初始化自更新', (tester) async {
    usePhoneSurface(tester);
    await tester.pumpWidget(
      goldenApp(
        home: const AboutPage(),
        brightness: Brightness.light,
        overrides: [
          operatingSystemProvider.overrideWithValue('android'),
          appUpdateProvider.overrideWith(() => throw StateError('Android 不应初始化自更新')),
        ],
      ),
    );
    await tester.pumpAndSettle();

    expect(AppInfo.androidVersionName, '${AppInfo.version.split('+').first}.dev');
    expect(find.text(AppInfo.androidDisplayVersion), findsOneWidget);
    expect(find.byType(AppUpdateTiles), findsNothing);
  });
}
