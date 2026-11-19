#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
JAVA_HOME=${JAVA_HOME:-/misc/scratch/aab5473/testing-tools/temurin-jdk21}
ASM=${ASM:-/misc/scratch/aab5473/testing-tools/maven-repository/org/ow2/asm/asm/9.9/asm-9.9.jar}
mkdir -p build/patch build/tools
"$JAVA_HOME/bin/javac" -cp "$ASM" -d build/tools src/Transform.java
"$JAVA_HOME/bin/java" -cp "build/tools:$ASM" Transform build/patch
"$JAVA_HOME/bin/javac" --patch-module java.base=src -d build/patch src/java/util/HashtableWitness.java
"$JAVA_HOME/bin/javac" -d build/tools src/Check.java
"$JAVA_HOME/bin/java" --patch-module java.base=build/patch -cp build/tools Check
