#!/usr/bin/perl
# Convert grouped tab-separated credential entries (input.tsv) into a Password Safe v3 vault.
use strict;
use warnings;
use Crypt::PWSafe3;

if (@ARGV && ($ARGV[0] eq '--help' || $ARGV[0] eq '-h')) {
    print "Usage: convert.pl <input.tsv> <output.psafe3> [password]\n";
    print "Password may also be provided via PWSAFE3_PASSWORD environment variable.\n";
    exit 0;
}

my $input_file  = $ARGV[0];
my $output_file = $ARGV[1];
my $password    = defined($ARGV[2]) ? $ARGV[2] : $ENV{PWSAFE3_PASSWORD};

die "Usage: convert.pl <input.tsv> <output.psafe3> [password]\n"
    unless defined($input_file) && defined($output_file) && defined($password) && length($password);
die "Input file '$input_file' not found\n" unless -f $input_file;
die "Output file '$output_file' already exists\n" if -e $output_file;

my $whoami = $ENV{USER} || 'pwsafe3';
my $vault = Crypt::PWSafe3->new(
    whoami   => $whoami,
    create   => 1,
    file     => $output_file,
    password => $password,
);

open my $input, '<', $input_file or die "Could not open $input_file: $!";
my $group = '';
while (my $line = <$input>) {
    $line =~ s/^\s+|\s+$//g;
    next if $line =~ /^$/;
    if ($line =~ /^GROUP:(.*)$/) {
        $group = $1;
        $group =~ s/^\s+|\s+$//g;
        next;
    }
    my @entry = split(/\t/, $line, -1);
    if (scalar(@entry) < 5) {
        warn "Skipping malformed TSV line $.: expected 5 tab-separated fields\n";
        next;
    }
    $vault->newrecord(
        user   => $entry[2] . '@' . $entry[1],
        passwd => $entry[4],
        title  => $entry[0],
        group  => $group,
        notes  => "Server: $entry[0]\nDatabase: $entry[1]\nAccess Type: $entry[3]",
    );
}
close($input);

my $header = Crypt::PWSafe3::HeaderField->new(name => 'savedonhost', value => 'localhost');
$vault->addheader($header);
$vault->markmodified();
$vault->save();

print $vault->getheader('wholastsaved')->value(), "\n";
print scalar localtime($vault->getheader('lastsavetime')->value()), "\n";
